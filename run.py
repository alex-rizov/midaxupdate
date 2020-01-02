# the run class
from midaxupdate.update_runner import UpdaterRunner
import os.path


def main():
        UpdaterRunner(os.getcwd(), os.getcwd()).run()


if __name__ == "__main__":
    main()