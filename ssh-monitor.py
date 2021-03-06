#!/bin/python

# Must configure logging before importing modules as they overwrite config
import logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

import time
import os
import argparse
import traceback
from importlib import import_module

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from apscheduler.schedulers.background import BackgroundScheduler
from task_parser import TaskParser

# Lower the modules logging level
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger('ssh-manager')


def createClass(task):
    MyClass = getattr(import_module('task.' + task.task), task.task)
    return MyClass(task)


def parse_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', required=True, help='Task folder to be watched')
    return vars(ap.parse_args())


def addJob(task, scheduler):
    try:
        t = createClass(task)
        scheduler.add_job(
            t.execute,
            'interval',
            seconds=task.interval,
            id=task.id)
        logger.info("Added task: %s - interval: %d", task.id, task.interval)
    except:
        logger.error(traceback.format_exc)


class YmlFileEventHandler(PatternMatchingEventHandler):

    def set_scheduler(self, scheduler):
        self.scheduler = scheduler

    def set_parser(self, parser):
        self.parser = parser

    def on_modified(self, event):
        id = os.path.basename(event.src_path).replace('.yml', '')
        logger.warning("File modified: %s", event.src_path)
        try:
            self.scheduler.remove_job(id)
        except:
            pass  # We don't care if we don't find the task

        self.parser.parse()
        task = filter(lambda x: x.id == id, self.parser.task_list)
        if len(task) == 0:
            logging.error("Could not find task with ID: %s", id)
        addJob(task[0], self.scheduler)

    def on_deleted(self, event):
        id = os.path.basename(event.src_path).replace('.yml', '')
        logger.warning("File deleted: %s", event.src_path)
        self.scheduler.remove_job(id)

    def on_moved(self, event):
        id = os.path.basename(event.src_path).replace('.yml', '')
        logger.warning("File moved: %s", event.src_path)

        if os.path.exists(event.src_path + '.yml'):
            # New job
            task = filter(lambda x: x.id == id, self.parser.task_list)
            if len(task) == 0:
                logging.error("Could not find task with ID: %s", id)
            addJob(task[0], self.scheduler)
        else:
            # Remove rob
            self.scheduler.remove_job(id)

    def on_created(self, event):
        self.parser.parse()
        id = os.path.basename(event.src_path).replace('.yml', '')
        logger.warning("File added: %s", event.src_path)
        task = filter(lambda x: x.id == id, self.parser.task_list)
        if len(task) == 0:
            logging.error("Could not find task with ID: %s", id)
        addJob(task[0], self.scheduler)


def main(args):
    scheduler = BackgroundScheduler(coalesce=True, misfire_grace_time=4)
    taskparser = TaskParser(args['f'])
    taskparser.parse()

    yml_handler = YmlFileEventHandler(patterns=["*.yml"])
    yml_handler.set_scheduler(scheduler)
    yml_handler.set_parser(taskparser)
    file_observer = Observer()
    file_observer.schedule(yml_handler, path=args['f'], recursive=False)
    file_observer.start()

    # Initial parsing of the task folder
    for t in taskparser.task_list:
        addJob(t, scheduler)
        # Spread tasks from each other to prevent overload/task miss
        time.sleep(1)

    scheduler.start()

    # Update jobs while running
    while True:
        try:
            time.sleep(15)
        except KeyboardInterrupt:
            break

    scheduler.shutdown()

if __name__ == '__main__':
    main(parse_arguments())
