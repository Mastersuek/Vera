import os
import re
import logging
from datetime import datetime
import argparse

def setup_logging():
    """Настройка логирования для анализатора"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'log_analyzer')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'log_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('log_analyzer')

def analyze_test_logs(log_dir):
    """Анализ логов тестов"""
    logger = setup_logging()
    
    # Паттерны для поиска в логах
    patterns = {
        'error': r'\[Error\] (.+)',
        'failed': r'FAILED: (.+)',
        'passed': r'PASSED',
        'test_start': r'=== Starting test (.+)',
        'test_finished': r'=== Finished test (.+)',
        'assertion': r'\[Assert\] (.+)',
        'step': r'\[Step\] (.+)'
    }
    
    # Статистика тестов
    stats = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': [],
        'failed_tests': [],
        'test_durations': {}
    }
    
    # Проходим по всем логам тестов
    for log_file in os.listdir(log_dir):
        if log_file.startswith('test_') and log_file.endswith('.log'):
            logger.info(f"Analyzing {log_file}")
            
            with open(os.path.join(log_dir, log_file), 'r') as f:
                content = f.read()
                
                # Поиск ошибок
                errors = re.findall(patterns['error'], content)
                if errors:
                    stats['errors'].extend(errors)
                    
                # Поиск проваленных тестов
                failed = re.findall(patterns['failed'], content)
                if failed:
                    stats['failed_tests'].extend(failed)
                    stats['failed'] += 1
                else:
                    stats['passed'] += 1
                    
                # Статистика по тестам
                test_starts = re.findall(patterns['test_start'], content)
                test_finishes = re.findall(patterns['test_finished'], content)
                
                for test in test_starts:
                    if test in test_finishes:
                        stats['total_tests'] += 1
                        
    # Вывод результатов
    logger.info("=== Test Analysis Results ===")
    logger.info(f"Total tests: {stats['total_tests']}")
    logger.info(f"Passed: {stats['passed']}")
    logger.info(f"Failed: {stats['failed']}")
    
    if stats['errors']:
        logger.error("=== Errors Found ===")
        for error in stats['errors']:
            logger.error(error)
    
    if stats['failed_tests']:
        logger.error("=== Failed Tests ===")
        for test in stats['failed_tests']:
            logger.error(test)

def main():
    parser = argparse.ArgumentParser(description='Analyze test logs')
    parser.add_argument('--log-dir', '-d', default='logs/tests', help='Directory containing test logs')
    
    args = parser.parse_args()
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.log_dir)
    analyze_test_logs(log_dir)

if __name__ == '__main__':
    main()
