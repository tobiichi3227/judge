import os
import json
from collections import deque
from tornado import gen, concurrent
from tornado.ioloop import IOLoop, PollIOLoop
from tornado.web import Application, RequestHandler
from tornado.websocket import WebSocketHandler
import PyExt
import Privilege
import Config
from StdChal import StdChal


class UVIOLoop(PollIOLoop):
    def initialize(self, **kwargs):
        super().initialize(impl = PyExt.UvPoll(), **kwargs)


class JudgeHandler(WebSocketHandler): 
    chal_running_count = 0
    chal_queue = deque()

    @gen.coroutine
    def start_chal(obj, ws):
        chal_id = obj['chal_id']
        code_path = '/srv/nfs' + obj['code_path'][4:]
        test_list = obj['testl']
        res_path = '/srv/nfs' + obj['res_path'][4:]

        test_paramlist = list()
        comp_type = test_list[0]['comp_type']
        assert(comp_type in ['g++', 'clang++', 'makefile', 'python3'])

        for test in test_list:
            assert(test['comp_type'] == comp_type)
            assert(test['check_type'] == 'diff')
            test_idx = test['test_idx']
            memlimit = test['memlimit']
            timelimit = test['timelimit']
            data_ids = test['metadata']['data']
            for data_id in data_ids:
                test_paramlist.append({
                    'in': res_path + '/testdata/%d.in'%data_id,
                    'ans': res_path + '/testdata/%d.out'%data_id,
                    'timelimit': timelimit,
                    'memlimit': memlimit,
                })

        chal = StdChal(chal_id, code_path, comp_type, res_path, test_paramlist)
        result_list = yield chal.start()

        idx = 0
        for test in test_list:
            test_idx = test['test_idx']
            data_ids = test['metadata']['data']
            total_runtime = 0
            total_mem = 0
            total_status = 0
            for data_id in data_ids:
                runtime, peakmem, status = result_list[idx]
                total_runtime += runtime
                total_mem += peakmem
                total_status = max(total_status, status)
                idx += 1

            ws.write_message(json.dumps({
                'chal_id': chal_id,
                'test_idx': test_idx,
                'state': total_status,
                'runtime': total_runtime,
                'memory': total_mem,
            }))

        JudgeHandler.chal_running_count -= 1
        JudgeHandler.emit_chal()

    def emit_chal(obj=None, ws=None):
        if obj is not None:
            JudgeHandler.chal_queue.append((obj, ws))

        while len(JudgeHandler.chal_queue) > 0 \
            and JudgeHandler.chal_running_count < Config.TASK_MAXCONCURRENT:
            chal = JudgeHandler.chal_queue.popleft()
            JudgeHandler.chal_running_count += 1
            IOLoop.instance().add_callback(JudgeHandler.start_chal, *chal)

    def open(self): 
        pass 

    def on_message(self, msg): 
        obj = json.loads(msg, 'utf-8')
        JudgeHandler.emit_chal(obj, self)

    def on_close(self): 
        pass


@concurrent.return_future
def test(callback):
    def _done_cb(task_id, stat):
        print(stat)
        callback()

    task_id = PyExt.create_task('/usr/bin/python3.4',
        ['-m', 'py_compile', '/test.py'],
        ['HOME=/'],
        0, 1, 2,
        '/', 'container/standard',
        10000, 10000, 100000000, 256 * 1024 * 1024,
        PyExt.RESTRICT_LEVEL_HIGH)
    PyExt.start_task(task_id, _done_cb)


def main():
    Privilege.init()
    PyExt.init()
    StdChal.init()
    IOLoop.configure(UVIOLoop)

    app = Application([
        (r'/judge', JudgeHandler),
    ])
    app.listen(2501)

    #IOLoop.instance().add_callback(test)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
