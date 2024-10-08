import multiprocessing
from src.main import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
