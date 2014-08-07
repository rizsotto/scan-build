# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import multiprocessing
import threading


def _produce_to_queue(func, queue, task):
    queue.put(func(task))


def _consume_from_queue(func, queue, result):
    for e in iter(queue.get, 'STOP'):
        func(result, e)


def run(input_iterable, produce_func, consume_func, output):
    queue = multiprocessing.Manager().Queue()

    consumer = threading.Thread(target=_consume_from_queue,
                                args=(consume_func, queue, output))
    consumer.start()

    pool = multiprocessing.Pool()
    for task in input_iterable:
        pool.apply_async(func=_produce_to_queue,
                         args=(produce_func, queue, task))
    pool.close()
    pool.join()

    queue.put('STOP')
    consumer.join()

    return output
