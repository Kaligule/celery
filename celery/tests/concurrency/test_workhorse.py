from __future__ import absolute_import

import errno
import os
import signal
import socket
import time
from itertools import cycle
from contextlib import closing

from celery.concurrency.workhorse import TaskPool
from celery.five import items
from celery.five import range
from celery.tests.case import AppCase
from celery.tests.case import call
from celery.tests.case import Mock
from celery.tests.case import patch
from celery.tests.case import SkipTest
from celery.utils.functional import noop
from kombu.async.semaphore import LaxBoundedSemaphore

class test_Workhorse(AppCase):

    def setup(self):
        if not hasattr(os, 'fork'):
            raise SkipTest('missing os.fork')

    def test_run_stop_pool(self):
        pool = TaskPool(semaphore=LaxBoundedSemaphore(10))
        with closing(pool):
            pool.start()


            pids = []
            accept_callback = lambda pid, ts: pids.append(pid)
            success_callback = Mock()
            error_callback = Mock()
            pool.apply_async(
                lambda x: x,
                (2, ),
                {},
                accept_callback=accept_callback,
                correlation_id='asdf-1234',
                error_callback=error_callback,
                callback=success_callback,
            )
            self.assertTrue(pool.workers)
            self.assertEqual(pids, list(pool.workers))
            pool.stop()
            success_callback.assert_called_with(None)
            self.assertFalse(error_callback.called)

    def test_terminate_pool(self):
        pool = TaskPool(semaphore=LaxBoundedSemaphore(10))
        with closing(pool):
            pool.start()
            pids = []
            accept_callback = lambda pid, ts: pids.append(pid)
            success_callback = Mock()
            error_callback = Mock()
            pool.apply_async(
                lambda x: time.sleep(x),
                (2, ),
                {},
                accept_callback=accept_callback,
                correlation_id='asdf-1234',
                error_callback=error_callback,
                callback=success_callback,
            )
            self.assertTrue(pool.workers)
            self.assertEqual(len(pids), 1)
            self.assertEqual(pids, list(pool.workers))
            pool.terminate()
            self.assertFalse(success_callback.called)
            pool.stop()
            self.assertTrue(error_callback.called)

    def test_release_sem(self):
        semaphore = LaxBoundedSemaphore(1)
        pool = TaskPool(semaphore=semaphore)
        with closing(pool):
            pool.start()
            pids = []
            accept_callback = lambda pid, ts: pids.append(pid)
            success_callback = Mock()
            error_callback = Mock()
            for i in range(3):
                semaphore.acquire(
                    lambda args, kwargs: pool.apply_async(*args, **kwargs),
                    (lambda x: time.sleep(x), (2, ), {}),
                    dict(
                        accept_callback=accept_callback,
                        correlation_id='asdf-1234-%s' % i,
                        error_callback=error_callback,
                        callback=success_callback,
                    )
                )
            self.assertEqual(semaphore.value, 0)
            self.assertTrue(pool.workers)
            self.assertEqual(pids, list(pool.workers))
            self.assertEqual(len(pids), 1)
            pool.terminate_job(pids[0], signal.SIGTERM)
            pool.terminate()
        # TODO TODO TODO TODO TODO TODO
        #pool.grow()
        #self.assertFalse(success_callback.called)
        #self.assertTrue(error_callback.called)

    #def test_restart
    #
    #def test_timeout
    #
    #def test_