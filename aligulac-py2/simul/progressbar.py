# -*- coding: utf-8 -*-

import sys
import time

class ProgressBar:
    def __init__(self, duration, exp=''):
        self.exp = exp
        self.duration = duration
        self.prog_bar = '[]'
        self.fill_char = '—'
        self.width = 40
        self.__update_amount(0)

    def animate(self):
        for i in range(self.duration):
            print(self.dyn_str())
            self.update_time(i + 1)
            time.sleep(1) 
        print(self)

    def update_time(self, elapsed_secs):
        self.__update_amount((elapsed_secs / float(self.duration)) * 100.0)
        self.prog_bar += '  %d/%s' % (elapsed_secs, self.duration)

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[' + self.fill_char * num_hashes +\
                ' ' * (all_full - num_hashes) + ']'
        pct_place = (len(self.prog_bar) // 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.exp + ': ' + self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])

    def dyn_str(self):
        if sys.platform.lower().startswith('win'):
            return str(self) + '\r'
        else:
            return str(self) + chr(27) + '[A'

    def __str__(self):
        return str(self.prog_bar)
