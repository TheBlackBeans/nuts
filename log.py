#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'BlackBeans'

import datetime, os, gzip

class Logger:
    def __init__(self, dir_, custom_name='', custom_type='date', custom_format='[{source}] [{type}] [{time}] {message}', verbosity=0, compresslevel=9, stdout=False):
        self.compresslevel = compresslevel
        self.verbosity = verbosity
        self.stdout = False
        if isinstance(dir_, (list, tuple)):
            self.dir = os.sep.join(dir_)
        elif isinstance(dir_, str):
            self.dir = dir_
        else:
            raise TypeError('dir_ should be string, list or tuple, not %s' % type(dir_))

        if custom_type == 'date':
            self.name = 'log-' + str(datetime.datetime.now()).split('.')[0].replace(' ', '_') + '.log.gz'
        elif custom_type == 'custom':
            self.name = custom_name + '.gz'
        else:
            raise ValueError('custom_type can be custom or date, not %s' % custom_type)

        self.custom_format = custom_format
        self._buffer = []
        self.file = None
    def open(self):
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        self.file = open(os.sep.join([self.dir, 'latest.log']), 'w')
        
    def write(self, message, source='main', type_='info', end="\n", verbosity=0):
        if verbosity > self.verbosity: return
        now = datetime.datetime.time(datetime.datetime.now())
        self._buffer.append(self.custom_format.format(
            source=source,
            type=type_,
            time=':'.join([str(now.hour), str(now.minute), str(now.second)]),
            message=message
            ) + end
        )

    def flush(self):
        if self.stdout: print("\n".join(self._buffer))
        self.file.writelines(self._buffer)
        self.file.flush()
        self._buffer = []
        
    def compress(self):
        with open(os.sep.join([self.dir, 'latest.log']), 'rb') as f:
            with open(os.sep.join([self.dir, self.name]), 'wb') as f2:
                f2.write(gzip.compress(f.read()))
    def close(self):
        self.flush()
        self.compress()
        self.file.close()
