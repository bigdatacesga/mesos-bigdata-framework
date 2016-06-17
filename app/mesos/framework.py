"""Big Data Mesos Framework"""
import logging
import os
from threading import Thread

from mesos.interface import mesos_pb2
from mesos.native import MesosSchedulerDriver
from scheduler import BigDataScheduler

logger = logging.getLogger(__name__)

driver = None
scheduler = None
STARTED = False


def submit(cluster):
    """Submit a cluster instance to Mesos"""
    scheduler.enqueue(cluster)


def kill(cluster):
    taskid = mesos_pb2.TaskID()
    taskid.value = str(cluster).replace("/", "_").replace(".", "-")
    driver.killTask(taskid)

    # service = registry.Cluster(instance_id)
    # nodesList = service.nodes
    # for node in nodesList:
    #     clusterid = node.clusterid + "_" + node.name
    #     message = TaskID()
    #     message.value = clusterid
    #     self.driver.killTask(message)


def pending():
    return scheduler.pending()


def start(master):
    """Start the Big Data framework"""
    global driver, scheduler

    if driver and scheduler:
        return driver, scheduler

    executor = mesos_pb2.ExecutorInfo()
    executor.executor_id.value = 'BigDataExecutor'
    executor.name = executor.executor_id.value
    executor.command.value = '/usr/local/mesos/bin/paas-executor.py'

    framework = mesos_pb2.FrameworkInfo()
    framework.user = ''  # the current user
    framework.name = 'PaaS'
    framework.checkpoint = True

    scheduler = BigDataScheduler(executor)

    implicitAcknowledgements = 1

    if os.getenv('MESOS_AUTHENTICATE'):
        logger.info('Enabling framework authentication')

        credential = mesos_pb2.Credential()
        credential.principal = os.getenv('MESOS_PRINCIPAL')
        credential.secret = os.getenv('MESOS_SECRET')
        framework.principal = os.getenv('MESOS_PRINCIPAL')

        driver = MesosSchedulerDriver(scheduler, framework, master,
                                      implicitAcknowledgements, credential)
    else:
        framework.principal = framework.name
        driver = MesosSchedulerDriver(scheduler, framework, master, implicitAcknowledgements)

    # driver.run() blocks, so we run it in a separate thread.
    # This way, we can catch a SIGINT to kill the framework.
    def run_driver_thread():
        status = 0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1
        return status

    driver_thread = Thread(target=run_driver_thread, args=())
    # Stop abruptly the thread if the main process exits
    #driver_thread.setDaemon(True)
    driver_thread.start()

    logger.info('Scheduler running')

    return driver, scheduler


def stop():
    """Stop the framework"""
    global driver, scheduler
    logger.info('Shutting down scheduler')
    driver.stop()
    driver = None
    scheduler = None
