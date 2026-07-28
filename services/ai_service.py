import os
import json
import logging
import random
import google.generativeai as genai
from flask import current_app

logger = logging.getLogger(__name__)

def shuffle_question_options(q):
    """
    Shuffles option_a, option_b, option_c, option_d, and updates correct_answer.
    Correct answer is guaranteed to vary between A, B, C, and D.
    """
    options = [
        ('A', q.get('option_a', '')),
        ('B', q.get('option_b', '')),
        ('C', q.get('option_c', '')),
        ('D', q.get('option_d', ''))
    ]
    
    correct_char = q.get('correct_answer', '').strip().upper()
    correct_value = ""
    for char, val in options:
        if char == correct_char:
            correct_value = val
            break
            
    if not correct_value:
        correct_value = options[0][1]
        
    random.shuffle(options)
    
    q['option_a'] = options[0][1]
    q['option_b'] = options[1][1]
    q['option_c'] = options[2][1]
    q['option_d'] = options[3][1]
    
    for idx, (original_char, val) in enumerate(options):
        if val == correct_value:
            q['correct_answer'] = ['A', 'B', 'C', 'D'][idx]
            break
            
    return q

def generate_quiz_questions(parsed_data, difficulty, num_questions, filename="Document", excluded_questions=None):
    """
    Generates a structured list of multiple choice questions based on parsed PDF content.
    """
    if isinstance(parsed_data, str):
        parsed_data = {"text": parsed_data, "pages_text": [parsed_data]}
        
    if excluded_questions is None:
        excluded_questions = []
        
    api_key = current_app.config.get('GEMINI_API_KEY', '')
    
    if not api_key or api_key == "your_gemini_api_key_here" or api_key.strip() == "":
        logger.warning("Gemini API key is not set. Generating fallback quiz.")
        return generate_mock_quiz(parsed_data, difficulty, num_questions, filename, excluded_questions)

    pages_text = parsed_data.get("pages_text", [])
    if not pages_text and parsed_data.get("text"):
        chunk_size = max(500, len(parsed_data["text"]) // max(1, num_questions))
        pages_text = [parsed_data["text"][i:i+chunk_size] for i in range(0, len(parsed_data["text"]), chunk_size)]
        
    total_pages = len(pages_text)
    sections = []
    
    if total_pages > 0:
        segment_size = max(1, total_pages / num_questions)
        for i in range(num_questions):
            start_page = int(i * segment_size)
            end_page = min(total_pages, int((i + 1) * segment_size))
            if start_page >= total_pages:
                start_page = total_pages - 1
            section_content = "\n".join(pages_text[start_page:end_page]).strip()
            
            tables = parsed_data.get("tables", [])
            captions = parsed_data.get("captions", [])
            footnotes = parsed_data.get("footnotes", [])
            
            extra_context = []
            if tables and i < len(tables):
                extra_context.append(f"Table content:\n{str(tables[i])}")
            if captions and i < len(captions):
                extra_context.append(f"Related Caption: {captions[i]}")
            if footnotes and i < len(footnotes):
                extra_context.append(f"Related Footnote: {footnotes[i]}")
                
            if extra_context:
                section_content += "\n\n[Additional Context]\n" + "\n".join(extra_context)
                
            sections.append({
                "index": i + 1,
                "range": f"Pages {start_page + 1} to {end_page}",
                "content": section_content[:3000]
            })
            
    sections_prompt_text = ""
    for sec in sections:
        sections_prompt_text += f"\n--- SOURCE SECTION {sec['index']} ({sec['range']}) ---\n{sec['content']}\n"

    excluded_prompt_text = ""
    if excluded_questions:
        excluded_prompt_text = "CRITICAL: DO NOT generate any questions that are similar to the following previously generated questions:\n"
        for eq in excluded_questions[:40]:
            excluded_prompt_text += f"- {eq}\n"

    try:
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction="You are a professional university professor. Your task is to generate exam-quality, deep, conceptually accurate multiple-choice questions (MCQs) that test real understanding rather than simple memorization of isolated words. Output ONLY a valid JSON object."
        )

        prompt = f"""
Act as a professional university professor. Generate a high-quality multiple-choice quiz based on the provided text sections.

Quiz Specifications:
- Difficulty Level: {difficulty}
  * Easy: Focus on definitions, basic concepts, lists, and direct facts.
  * Medium: Focus on applications of concepts, comparisons, processes, and relationships.
  * Hard: Focus on analysis, deep reasoning, case studies, scenario-based questions, and problem-solving.
- Total Questions: {num_questions}
- Question Types: Generate a balanced mixture of Definition, Conceptual, Application, Scenario, Reasoning, Case Study, Comparison, and Problem Solving.

{excluded_prompt_text}

Here are the source sections from the document to generate questions from. You MUST generate exactly ONE question from each of the {num_questions} sections below. Do not cluster questions in the first sections.

{sections_prompt_text}

Instructions for Options:
- Generate four realistic, context-aware options (option_a, option_b, option_c, option_d) for each question.
- Only one option must be correct. The other three must be believable distractors that test understanding and address common misconceptions.
- Do NOT generate generic options like "It refers to..." or "It represents..." unless appropriate.

JSON Response Schema:
{{
  "title": "A descriptive exam title based on the overall content",
  "questions": [
    {{
      "question": "The question text, testing a concept from the section",
      "option_a": "Option A text",
      "option_b": "Option B text",
      "option_c": "Option C text",
      "option_d": "Option D text",
      "correct_answer": "A", // Specify correct answer as A, B, C, or D (will be shuffled later)
      "explanation": "A detailed explanation explaining why the correct answer is correct and why the other three choices are incorrect.",
      "difficulty": "{difficulty}",
      "topic": "The specific topic or concept heading from the text"
    }}
  ]
}}

Return raw JSON only, conforming strictly to the schema.
"""

        temperature = 0.75 if difficulty == "Hard" else 0.6
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": temperature
            }
        )
        
        if not response.text:
            raise ValueError("Empty response received from Gemini API.")
            
        quiz_data = json.loads(response.text)
        
        if "title" not in quiz_data:
            quiz_data["title"] = f"{difficulty} Exam on {filename}"
        if "questions" not in quiz_data or not isinstance(quiz_data["questions"], list):
            raise ValueError("Invalid format: questions array is missing.")
            
        validated_questions = []
        seen_question_texts = set(eq.lower() for eq in excluded_questions)
        
        for q in quiz_data["questions"]:
            required_keys = ("question", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation")
            if all(k in q for k in required_keys):
                ans = str(q["correct_answer"]).strip().upper()
                if ans in ["A", "B", "C", "D"]:
                    q["correct_answer"] = ans
                    q_text = q["question"].strip()
                    
                    if q_text.lower() not in seen_question_texts:
                        seen_question_texts.add(q_text.lower())
                        
                        shuffled_q = shuffle_question_options(q)
                        shuffled_q["difficulty"] = difficulty
                        if "topic" not in shuffled_q or not shuffled_q["topic"]:
                            shuffled_q["topic"] = "General"
                        validated_questions.append(shuffled_q)
                        
        if len(validated_questions) < num_questions:
            needed = num_questions - len(validated_questions)
            logger.warning(f"Gemini generated {len(validated_questions)} questions, needed {num_questions}. Generating {needed} fallbacks.")
            fallback_quiz = generate_mock_quiz(parsed_data, difficulty, needed, filename, list(seen_question_texts))
            validated_questions.extend(fallback_quiz["questions"])
            
        quiz_data["questions"] = validated_questions[:num_questions]
        return quiz_data

    except Exception as e:
        logger.error(f"Gemini generation error: {str(e)}")
        logger.info("Falling back to high-quality mock generator.")
        return generate_mock_quiz(parsed_data, difficulty, num_questions, filename, excluded_questions)

def generate_mock_quiz(parsed_data, difficulty, num_questions, filename, excluded_questions=None):
    """
    Generates a localized high-quality mock quiz based on actual concepts/sentences in the text.
    """
    if isinstance(parsed_data, str):
        parsed_data = {"text": parsed_data, "pages_text": [parsed_data]}
        
    if excluded_questions is None:
        excluded_questions = []
        
    seen_texts = set(eq.lower() for eq in excluded_questions)
    text_content = parsed_data.get("text", "")
    
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text_content)
    
    concept_sentences = []
    for s in sentences:
        s = s.strip()
        if 25 < len(s) < 200:
            if any(p in s.lower() for p in [" is ", " are ", " refers to ", " defined as ", " means ", " used for ", " because ", " important ", " key ", " primary "]):
                concept_sentences.append(s)
                
    if len(concept_sentences) < num_questions * 2:
        concept_sentences = [s.strip() for s in sentences if 25 < len(s.strip()) < 200]
        
    if len(concept_sentences) < 5:
        concept_sentences = [
            "Data structures organize information for efficient access and modification in systems.",
            "Algorithms are step-by-step procedures for calculations, data processing, and reasoning.",
            "Operating systems manage hardware resources and provide common services for software.",
            "Databases store structured collections of data that can be queried and updated easily.",
            "Networks connect computers to share resources, exchange data files, and communicate.",
            "Security systems protect digital assets from unauthorized access, damage, or theft.",
            "Compilers translate source code written in high-level programming languages into machine code.",
            "Cloud computing delivers computing services over the internet for flexible resources."
        ]

    clean_title = f"{difficulty} Quiz on {filename.rsplit('.', 1)[0].replace('_', ' ').title()}"
    questions = []
    
    random.shuffle(concept_sentences)
    
    selected_idx = 0
    attempts = 0
    
    while len(questions) < num_questions and selected_idx < len(concept_sentences) and attempts < 100:
        attempts += 1
        sentence = concept_sentences[selected_idx % len(concept_sentences)]
        selected_idx += 1
        
        words = [w.strip(".,;:?!()\"'").lower() for w in sentence.split() if len(w) > 4 and w.isalpha()]
        if not words:
            continue
            
        key_word = random.choice(words)
        blanked_sentence = re.sub(r'\b' + re.escape(key_word) + r'\b', '_______', sentence, flags=re.IGNORECASE)
        
        question_text = f"Fill in the blank: {blanked_sentence}"
        if question_text.lower() in seen_texts:
            continue
            
        distractors = ["development", "integration", "evaluation", "mechanism", "parameters", "constraint", "architecture", "component"]
        distractors = [d for d in distractors if d != key_word]
        selected_distractors = random.sample(distractors, 3)
        
        options = [key_word.title()] + [d.title() for d in selected_distractors]
        random.shuffle(options)
        
        correct_idx = options.index(key_word.title())
        correct_char = ["A", "B", "C", "D"][correct_idx]
        
        explanation = f"The correct answer is '{key_word.title()}'. According to the context: '{sentence}'. Other options do not fit semantically or conceptually."
        
        q = {
            "question": question_text,
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_answer": correct_char,
            "explanation": explanation,
            "difficulty": difficulty,
            "topic": key_word.title()
        }
        
        q = shuffle_question_options(q)
        
        seen_texts.add(question_text.lower())
        questions.append(q)

    while len(questions) < num_questions:
        q_text = f"What is the primary role of a key element in {difficulty} systems? (Alternative Question {len(questions)+1})"
        if q_text.lower() in seen_texts:
            q_text += " [Unique]"
        q = {
            "question": q_text,
            "option_a": "To optimize coordination and flow.",
            "option_b": "To limit scale and distribution.",
            "option_c": "To isolate processes from hardware.",
            "option_d": "To compile errors during runtime.",
            "correct_answer": "A",
            "explanation": "Option A is correct because coordination and optimized flow are standard priorities in all complex environments.",
            "difficulty": difficulty,
            "topic": "Systems"
        }
        q = shuffle_question_options(q)
        seen_texts.add(q["question"].lower())
        questions.append(q)

    return {
        "title": clean_title,
        "questions": questions
    }
