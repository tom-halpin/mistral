# Copyright 2014 - Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import datetime
import eventlet
import mock

from mistral.db.v2 import api as db_api
from mistral.services import scheduler
from mistral.tests import base
from mistral.workflow import utils as wf_utils


def factory_method():
    pass


class SchedulerServiceTest(base.DbTestCase):
    def setUp(self):
        super(SchedulerServiceTest, self).setUp()

        thread_group = scheduler.setup()
        self.addCleanup(thread_group.stop)

    @mock.patch('mistral.tests.unit.services.test_scheduler.factory_method')
    def test_scheduler_with_factory(self, factory):
        factory_method = ('mistral.tests.unit.services.'
                          'test_scheduler.factory_method')
        target_method = 'run_something'
        method_args = {'name': 'task', 'id': '123'}
        delay = 0.5

        scheduler.schedule_call(factory_method,
                                target_method,
                                delay,
                                **method_args)

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=1)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        call = self._assert_single_item(calls,
                                        target_method_name=target_method)

        self.assertIn('name', call['method_arguments'])

        eventlet.sleep(delay * 2)

        factory().run_something.assert_called_once_with(name='task', id='123')

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=1)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        self.assertEqual(0, len(calls))

    @mock.patch('mistral.tests.unit.services.test_scheduler.factory_method')
    def test_scheduler_without_factory(self, method):
        target_method = ('mistral.tests.unit.services.'
                         'test_scheduler.factory_method')
        method_args = {'name': 'task', 'id': '321'}
        delay = 0.5

        scheduler.schedule_call(None,
                                target_method,
                                delay,
                                **method_args)

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=0.5)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        call = self._assert_single_item(calls,
                                        target_method_name=target_method)

        self.assertIn('name', call['method_arguments'])

        eventlet.sleep(delay * 2)

        method.assert_called_once_with(name='task', id='321')

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=1)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        self.assertEqual(0, len(calls))

    @mock.patch('mistral.tests.unit.services.test_scheduler.factory_method')
    def test_scheduler_with_serializer(self, factory):
        factory_method = ('mistral.tests.unit.services.'
                          'test_scheduler.factory_method')
        target_method = 'run_something'

        task_result = wf_utils.TaskResult('data', 'error')

        method_args = {
            'name': 'task',
            'id': '123',
            'result': task_result}

        serializers_map = {
            'result': 'mistral.workflow.utils.TaskResultSerializer'
        }

        delay = 0.5

        scheduler.schedule_call(factory_method,
                                target_method,
                                delay,
                                serializers=serializers_map,
                                **method_args)

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=0.5)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        self.assertEqual(1, len(calls))
        call = self._assert_single_item(calls,
                                        target_method_name=target_method)

        self.assertIn('name', call['method_arguments'])

        eventlet.sleep(delay * 2)

        result = factory().run_something.call_args[1].get('result')

        self.assertIsInstance(result, wf_utils.TaskResult)
        self.assertEqual('data', result.data)
        self.assertEqual('error', result.error)

        time_filter = datetime.datetime.now() + datetime.timedelta(seconds=1)
        calls = db_api.get_delayed_calls_to_start(time_filter)

        self.assertEqual(0, len(calls))
