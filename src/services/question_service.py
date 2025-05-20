import logging
import asyncio
import random
from typing import List, Dict, Any, Set, Optional
from services.database import Database
from services.ai_service import AIService
from config.constants import DEFAULT_QUESTIONS_PER_TEST, MAX_OPTION_LENGTH

class QuestionService:
    def __init__(self, db: Database, ai_service: AIService):
        self.db = db
        self.ai_service = ai_service

    async def get_or_generate_tasks(
        self,
        user_id: int,
        topic: str,
        needed: int = DEFAULT_QUESTIONS_PER_TEST,
        force_ai: bool = False,
        existing_question_texts_to_exclude: Optional[Set[str]] = None
    ) -> List[tuple]:
        """Get tasks from DB or generate new ones if needed."""
        if existing_question_texts_to_exclude is None:
            existing_question_texts_to_exclude = set()
        
        tasks = []
        
        # First get regular tasks from database
        db_tasks_pool_raw = self.db.get_tasks_for_topic(topic, limit=needed * 2)
        
        # Filter out excluded questions and convert to list of tuples
        for task in db_tasks_pool_raw:
            if task['question'] not in existing_question_texts_to_exclude:
                tasks.append((
                    task['question'],
                    task['answer'],
                    task['explanation'],
                    task['incorrect_options'] or []
                ))
                existing_question_texts_to_exclude.add(task['question'])
                if len(tasks) >= needed:
                    break
        
        # If we have enough tasks, return them
        if len(tasks) >= needed:
            return tasks[:needed]
        
        # If not enough tasks, try to get error tasks
        error_tasks = self.db.get_error_tasks_for_user(user_id, topic, limit=needed)
        if error_tasks:
            logging.info(f"Found {len(error_tasks)} error tasks for user {user_id}, topic '{topic}'.")
            for task in error_tasks:
                if task['question'] not in existing_question_texts_to_exclude:
                    tasks.append((
                        task['question'],
                        task['answer'],
                        task['explanation'],
                        task['incorrect_options'] or []
                    ))
                    existing_question_texts_to_exclude.add(task['question'])
                    if len(tasks) >= needed:
                        break
        
        # If we have enough tasks now, return them
        if len(tasks) >= needed:
            return tasks[:needed]
        
        # If still not enough tasks, generate new ones
        remaining = needed - len(tasks)
        new_tasks = []
        
        # Generate tasks in parallel
        generation_tasks = [self.ai_service.generate_task(topic) for _ in range(remaining)]
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Error generating task: {result}")
                continue
            if result:
                question, correct_answer, incorrect_options, explanation = result
                if question not in existing_question_texts_to_exclude:
                    new_tasks.append((question, correct_answer, explanation, incorrect_options))
                    existing_question_texts_to_exclude.add(question)
        
        # Combine existing and new tasks
        all_tasks = tasks + new_tasks
        
        # If still not enough tasks, try one more time
        if len(all_tasks) < needed:
            logging.warning(f"Could only generate {len(all_tasks)} tasks out of {needed} needed. Trying one more time...")
            final_tasks = await self.get_or_generate_tasks(
                user_id, topic, needed, 
                force_ai=True,
                existing_question_texts_to_exclude=existing_question_texts_to_exclude
            )
            return final_tasks
        
        return all_tasks[:needed]

    @staticmethod
    def generate_universal_options(correct_answer_str: str) -> List[str]:
        """Generate universal options for a given correct answer."""
        import re
        correct_answer_str = str(correct_answer_str).strip()
        options = set()
        
        if len(correct_answer_str) <= MAX_OPTION_LENGTH:
            options.add(correct_answer_str)

        num_match = re.match(r"^(-?\d+([.,]\d+)?)\s*(.*)$", correct_answer_str.strip())
        generated_numeric_options = False

        if num_match:
            num_val_str = num_match.group(1)
            unit = num_match.group(3).strip()
            try:
                num_val = float(num_val_str.replace(',', '.'))
                is_int_val = num_val == int(num_val)
                if is_int_val:
                    num_val = int(num_val)
                possible_distractors = set()
                
                for i in range(15):
                    if len(options) + len(possible_distractors) >= 4 and i > 5:
                        break
                    op_choice = random.choice([-1, 1, -2, 2, 3, 4])
                    if op_choice == 1:
                        delta_abs = max(1, abs(num_val) * random.uniform(0.1, 0.5))
                        dist_candidate_val = num_val + delta_abs * (1 + random.random())
                    elif op_choice == -1:
                        delta_abs = max(1, abs(num_val) * random.uniform(0.1, 0.5))
                        dist_candidate_val = num_val - delta_abs * (1 + random.random())
                    elif op_choice == 2 and num_val != 0:
                        factor = random.choice([0.5, 1.5, 2, 0.75, 1.25, 1.75])
                        dist_candidate_val = num_val * factor
                    elif op_choice == -2 and num_val != 0:
                        factor = random.choice([2, 3, 4, 1.5])
                        dist_candidate_val = num_val / factor
                    elif op_choice == 3:
                        dist_candidate_val = num_val * (1 + random.uniform(0.1, 0.3))
                    else:
                        dist_candidate_val = num_val * (1 - random.uniform(0.1, 0.3))
                    
                    if is_int_val:
                        dist_candidate_val = round(dist_candidate_val)
                    else:
                        dist_candidate_val = round(dist_candidate_val, 2)
                    
                    if num_val > 0 and dist_candidate_val <= 0:
                        if num_val > 1 and is_int_val:
                            dist_candidate_val = max(1, round(num_val * random.uniform(0.1, 0.5)))
                        elif not is_int_val and num_val > 0.01:
                            dist_candidate_val = round(max(0.01, num_val * random.uniform(0.1, 0.5)), 2)
                        else:
                            dist_candidate_val = abs(dist_candidate_val) + (1 if is_int_val else 0.01)
                    
                    if unit:
                        option_str = f"{dist_candidate_val} {unit}".strip()
                    else:
                        option_str = str(dist_candidate_val)
                    
                    if option_str != correct_answer_str and len(option_str) <= MAX_OPTION_LENGTH:
                        possible_distractors.add(option_str)
                
                for distractor in list(possible_distractors):
                    if len(options) < 4:
                        options.add(distractor)
                    else:
                        break
                
                if len(options) > 1:
                    generated_numeric_options = True
                    
            except ValueError:
                pass

        if not generated_numeric_options or len(options) < 4:
            if len(correct_answer_str) > 0:
                base_options = set()
                for _ in range(10):
                    if len(base_options) >= 3:
                        break
                    if random.random() < 0.5:
                        words = correct_answer_str.split()
                        if len(words) > 1:
                            random.shuffle(words)
                            modified = ' '.join(words)
                            if modified != correct_answer_str and len(modified) <= MAX_OPTION_LENGTH:
                                base_options.add(modified)
                    else:
                        if len(correct_answer_str) > 3:
                            pos = random.randint(0, len(correct_answer_str) - 1)
                            modified = correct_answer_str[:pos] + correct_answer_str[pos + 1:]
                            if modified != correct_answer_str and len(modified) <= MAX_OPTION_LENGTH:
                                base_options.add(modified)
                
                for option in base_options:
                    if len(options) < 4:
                        options.add(option)

        final_options_list = list(options)
        if len(final_options_list) < 2:
            return []
        
        if correct_answer_str not in final_options_list and len(correct_answer_str) <= MAX_OPTION_LENGTH:
            if len(final_options_list) < 4:
                final_options_list.append(correct_answer_str)
        
        random.shuffle(final_options_list)
        return final_options_list[:4] 