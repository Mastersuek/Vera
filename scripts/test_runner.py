import subprocess
import logging
import os
import sys
from datetime import datetime
import argparse

def setup_logging():
    """Настройка логирования для тест-раннера"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'test_runner')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'test_runner_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('test_runner')

def run_tests(test_type=None, mark=None, verbose=False):
    """Запуск тестов"""
    logger = setup_logging()
    
    # Формируем команду для pytest
    command = ['pytest', 'tests/', '-v']
    
    if test_type:
        command.extend(['-k', test_type])
    
    if mark:
        command.extend(['-m', mark])
    
    if verbose:
        command.append('-s')
    
    logger.info(f"Starting test run with command: {' '.join(command)}")
    
    try:
        # Запуск тестов
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        logger.info("=== Test Output ===")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.error("=== Test Errors ===")
            logger.error(result.stderr)
        
        if result.returncode != 0:
            logger.error("Tests failed!")
            sys.exit(result.returncode)
        
        logger.info("All tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Run project tests')
    parser.add_argument('--type', '-t', help='Type of tests to run (e.g. unit, integration)')
    parser.add_argument('--mark', '-m', help='Run tests with specific pytest mark')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    run_tests(args.type, args.mark, args.verbose)

if __name__ == '__main__':
    main()
