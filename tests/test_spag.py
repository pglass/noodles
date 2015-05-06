import unittest
import subprocess
import os
import shutil
import json
import textwrap

import spag_remembers
import spag_files

# TODO: read this from a config?
SPAG_PROG = 'spag'
ENDPOINT = 'http://localhost:5000'
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')
V1_RESOURCES_DIR = os.path.join(RESOURCES_DIR, 'v1')
V2_RESOURCES_DIR = os.path.join(RESOURCES_DIR, 'v2')
SPAG_REMEMBERS_DIR = spag_remembers.SpagRemembers.DIR

def run_spag(*args):
    """
    :returns: A tuple (out, err, ret) where
        out is the output on stdout
        err is the output on stderr
        ret is the exit code
    """
    cmd = [SPAG_PROG] + list(args)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return (out.decode('utf-8'), err.decode('utf-8'), p.returncode)


class BaseTest(unittest.TestCase):

    @classmethod
    def _rm_remembers_dir(cls):
        try:
            # both os.removedirs and os.rmdir don't work on non-empty dirs
            shutil.rmtree(SPAG_REMEMBERS_DIR)
        except OSError as e:
            pass

    def setUp(self):
        super(BaseTest, self).setUp()
        run_spag('get', '/clear', '-e', ENDPOINT)
        run_spag('env', 'unset', '.', '--everything')
        self._rm_remembers_dir()

    def tearDown(self):
        self._rm_remembers_dir()
        super(BaseTest, self).tearDown()

class TestHeaders(BaseTest):

    def test_get_no_headers(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT)
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {})

    def test_get_one_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H', 'pglbutt:pglbutt')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt"})

    def test_get_two_headers(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT,
                                 '-H', 'pglbutt:pglbutt', '-H', 'wow:wow')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt", "Wow": "wow"})

    def test_get_no_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Error: -H option requires an argument\n')

    def test_get_invalid_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H', 'poo')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Error: Invalid header!\n')

    def test_show_headers(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-h')
        self.assertEqual(ret, 0)
        self.assertIn('content-type: application/json', out)


class TestGet(BaseTest):

    def test_get_no_endpoint(self):
        out, err, ret = run_spag('get', '/auth')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Endpoint not set\n\n')

    def test_get_supply_endpoint(self):
        out, err, ret = run_spag('get', '/auth', '-e', ENDPOINT)
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"token": "abcde"})

    def test_get_presupply_endpoint(self):
        out, err, ret = run_spag('env', 'set', ENDPOINT)
        self.assertEqual(out, 'endpoint: {0}\n\n'.format(ENDPOINT))
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        out, err, ret = run_spag('get', '/things')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"things": []})


class TestPost(BaseTest):

    def test_spag_post(self):
        run_spag('env', 'set', ENDPOINT)
        out, err, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "a"})
        self.assertEquals(err, '')

class TestPut(BaseTest):

    def test_spag_put(self):
        run_spag('env', 'set', ENDPOINT)
        out, err, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "a"})
        self.assertEquals(err, '')
        out, err, ret = run_spag('put', '/things/a', '--data', '{"id": "b"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "b"})
        self.assertEquals(err, '')

class TestPatch(BaseTest):

    def test_spag_patch(self):
        run_spag('env', 'set', ENDPOINT)
        out, err, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "a"})
        self.assertEquals(err, '')
        out, err, ret = run_spag('patch', '/things/a', '--data', '{"id": "b"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "b"})
        self.assertEquals(err, '')

class TestDelete(BaseTest):

    def test_spag_delete(self):
        run_spag('env', 'set', ENDPOINT)
        out, err, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "a"})
        self.assertEquals(err, '')
        out, err, ret = run_spag('delete', '/things/a', '--data', '{"id": "b"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(out, '\n')
        self.assertEquals(err, '')
        out, err, ret = run_spag('get', '/things')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"things": []})


class TestSpagFiles(BaseTest):

    def setUp(self):
        super(TestSpagFiles, self).setUp()
        run_spag('env', 'set', ENDPOINT)
        run_spag('env', 'set', '-E', 'dir=%s' % RESOURCES_DIR)
        self.table = spag_files.SpagFilesLookup(RESOURCES_DIR)

    def test_spag_lookup(self):
        expected = {
            'auth.yml': set([
                os.path.join(RESOURCES_DIR, 'auth.yml')]),
            'delete_thing.yml': set([
                os.path.join(RESOURCES_DIR, 'delete_thing.yml')]),
            'patch_thing.yml': set([
                os.path.join(V2_RESOURCES_DIR, 'patch_thing.yml')]),
            'post_thing.yml': set([
                os.path.join(V1_RESOURCES_DIR, 'post_thing.yml'),
                os.path.join(V2_RESOURCES_DIR, 'post_thing.yml')]),
            'get_thing.yml': set([
                os.path.join(V1_RESOURCES_DIR, 'get_thing.yml'),
                os.path.join(V2_RESOURCES_DIR, 'get_thing.yml')]),
            'headers.yml': set([
                os.path.join(RESOURCES_DIR, 'headers.yml')]),
        }
        self.assertEqual(self.table, expected)

    def test_spag_load_file(self):
        content = spag_files.load_file(os.path.join(RESOURCES_DIR, 'auth.yml'))
        self.assertEqual(content['method'], 'GET')
        self.assertEqual(content['uri'], '/auth')
        self.assertEqual(content['headers'], {'Accept': 'application/json'})

    def test_spag_request_get(self):
        for name in ('auth.yml', 'auth'):
            out, err, ret = run_spag('request', name)
            self.assertEqual(ret, 0)
            self.assertEqual(json.loads(out), {"token": "abcde"})
            self.assertEqual(err, '')

    def test_spag_request_post(self):
        out, err, ret = run_spag('request', 'v2/post_thing.yml')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"id": "c"})
        self.assertEqual(err, '')

    def test_spag_request_patch(self):
        # stuff in patch_thing.yml needs to match stuff here
        _, _, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                              '-H', 'content-type:application/json')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('request', 'patch_thing.yml')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"id": "c"})
        self.assertEqual(err, '')

    def test_spag_request_delete(self):
        for name in ('delete_thing.yml', 'delete_thing'):
            _, _, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                  '-H', 'content-type:application/json')
            self.assertEqual(ret, 0)
            out, err, ret = run_spag('request', name)
            self.assertEqual(ret, 0)
            self.assertEqual(out, '\n')
            self.assertEqual(err, '')

    def test_spag_request_data_option_overrides(self):
        out, err, ret = run_spag('request', 'v2/post_thing.yml',
                                 '--data', '{"id": "xyz"}',
                                 '-H', 'content-type:application/json')
        self.assertEqual(json.loads(out), {"id": "xyz"})
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

    def test_spag_request_headers_override(self):
        out, err, ret = run_spag('request', 'headers.yml',
                                 '-H', 'Hello:abcde')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"Hello": "abcde"})
        self.assertEqual(ret, 0)

    def test_spag_show_requests(self):
        out, err, ret = run_spag('request', '--show')
        def parse(text):
            return list(sorted(text.split()))
        expected = """
            tests/resources/auth.yml
            tests/resources/delete_thing.yml
            tests/resources/headers.yml
            tests/resources/v1/get_thing.yml
            tests/resources/v1/post_thing.yml
            tests/resources/v2/get_thing.yml
            tests/resources/v2/patch_thing.yml
            tests/resources/v2/post_thing.yml
            """
        self.assertEqual(err, '')
        self.assertEqual(parse(out), parse(expected))
        self.assertEqual(ret, 0)

    def test_spag_show_single_request(self):
        out, err, ret = run_spag('request', 'auth.yml', '--show')
        self.assertEqual(err, '')
        self.assertEqual(out.strip(),
            textwrap.dedent("""
            File tests/resources/auth.yml
            method: GET
            uri: /auth
            headers:
                Accept: "application/json"
            """).strip())
        self.assertEqual(ret, 0)

    def test_spag_environment_crud(self):
        out, err, ret = run_spag('env', 'set', 'abcdefgh')
        self.assertIn('endpoint: abcdefgh', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'show')
        self.assertIn('endpoint: abcdefgh', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'unset', 'endpoint', '--everything')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'show')
        self.assertEqual(out, '{}\n\n')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

    def test_spag_environment_activate_deactivate(self):
        out, err, ret = run_spag('env', 'unset', 'endpoint', '--everything')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'set', 'abcdefgh')
        self.assertIn('endpoint: abcdefgh', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'deactivate')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'show')
        self.assertIn('endpoint: abcdefgh', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

    def test_spag_set_environment_failure(self):
        out, err, ret = run_spag('env', 'set')
        self.assertEqual(err, 'Error: You must provide something to set!\n')
        self.assertNotEqual(ret, 0)

    def test_set_endoint_and_header(self):
        out, err, ret = run_spag('env', 'set', ENDPOINT, '-H', 'pglbutt:pglbutt')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertIn('headers', out)
        out, err, ret = run_spag('get', '/headers')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt"})


class TestSpagRemembers(BaseTest):

    def setUp(self):
        super(TestSpagRemembers, self).setUp()
        run_spag('env', 'set', ENDPOINT)

    def test_spag_remembers_request(self):
        auth_file = os.path.join(SPAG_REMEMBERS_DIR, 'v2/post_thing.yml')
        last_file = os.path.join(SPAG_REMEMBERS_DIR, 'last.yml')

        self.assertFalse(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertFalse(os.path.exists(auth_file))
        self.assertFalse(os.path.exists(last_file))

        _, err, ret = run_spag('request', 'v2/post_thing.yml',
                                 '--dir', RESOURCES_DIR)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertTrue(os.path.exists(auth_file))
        self.assertTrue(os.path.exists(last_file))

        auth_data = spag_files.load_file(auth_file)
        last_data = spag_files.load_file(last_file)

        # check the saved request data
        req = auth_data['request']
        self.assertEqual(set(req.keys()),
            set(['body', 'endpoint', 'uri', 'headers', 'method']))
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['endpoint'], ENDPOINT)
        self.assertEqual(req['uri'], '/things')
        self.assertEqual(req['headers']['Accept'], 'application/json')
        self.assertEqual(json.loads(req['body']), {"id": "c"})

        # check the saved response data
        resp = auth_data['response']
        self.assertEqual(set(resp.keys()), set(['body', 'headers', 'status']))
        self.assertEqual(resp['headers']['content-type'], 'application/json')
        self.assertEqual(resp['status'], 201)
        self.assertEqual(json.loads(resp['body']), {"id": "c"})

    def test_spag_remembers_get(self):
        self._test_spag_remembers_method_type('get')

    def test_spag_remembers_put(self):
        self._test_spag_remembers_method_type('put')

    def test_spag_remembers_post(self):
        self._test_spag_remembers_method_type('post')

    def test_spag_remembers_patch(self):
        self._test_spag_remembers_method_type('patch')

    def test_spag_remembers_delete(self):
        self._test_spag_remembers_method_type('delete')

    def _test_spag_remembers_method_type(self, method):
        filename = "{0}.yml".format(method)
        filepath = os.path.join(SPAG_REMEMBERS_DIR, filename)

        self.assertFalse(os.path.exists(filepath))

        _, err, ret = run_spag(method, '/poo', '--data', '{"id": "1"}')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(filepath))
