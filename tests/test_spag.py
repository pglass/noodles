import unittest
import subprocess
import os
import shutil
import json
import textwrap

import yaml

# TODO: read this from a config?
SPAG_PROG = os.environ.get('SPAG_TEST_EXE', './target/debug/spag')
print "Using spag at %s" % SPAG_PROG
ENDPOINT = 'http://localhost:5000'
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
V1_RESOURCES_DIR = os.path.join(RESOURCES_DIR, 'v1')
V2_RESOURCES_DIR = os.path.join(RESOURCES_DIR, 'v2')
SPAG_REMEMBERS_DIR = '.spag/remembers'
SPAG_HISTORY_FILE = '.spag/history.yml'

def rm_dir(dirname):
    try:
        # both os.removedirs and os.rmdir don't work on non-empty dirs
        shutil.rmtree(dirname)
    except OSError:
        pass

def rm_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

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

    # enable long diffs
    maxDiff = None

    def setUp(self):
        super(BaseTest, self).setUp()
        run_spag('get', '/clear', '-e', ENDPOINT)
        run_spag('env', 'unset', '--everything')
        rm_dir(SPAG_REMEMBERS_DIR)
        rm_file(SPAG_HISTORY_FILE)

    def tearDown(self):
        rm_dir(SPAG_REMEMBERS_DIR)
        rm_file(SPAG_HISTORY_FILE)
        super(BaseTest, self).tearDown()


class TestHeaders(BaseTest):

    def test_get_no_headers(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {})

    def test_get_one_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H', 'pglbutt:pglbutt')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt"})

    def test_get_two_headers(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT,
                                 '-H', 'pglbutt:pglbutt', '-H', 'wow:wow')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt", "Wow": "wow"})

    @unittest.skip('Fails correctly, but needs a better error msg')
    def test_get_no_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Error: -H option requires an argument\n')

    def test_get_invalid_header(self):
        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H', 'poo')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Invalid header "poo"\n')

    def test_passed_headers_override_environment(self):
        out, err, ret = run_spag('env', 'set', 'headers.a', 'b')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(yaml.load(out)['headers'].get('a'), 'b')

        out, err, ret = run_spag('get', '/headers', '-e', ENDPOINT, '-H', 'a: c')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out).get('A'), 'c')

class TestParams(BaseTest):

    def test_one_request_param(self):
        out, err, ret = run_spag('get', '/params?foo=bar', '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {'foo': 'bar'})

    def test_multiple_request_params(self):
        out, err, ret = run_spag('get', '/params?foo=bar&bar=baz&pglbutt=pglbutt', '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {'foo': 'bar',
                                           'bar': 'baz',
                                           'pglbutt': 'pglbutt'})

    def test_request_params_substitution(self):
        out, err, ret = run_spag('env', 'set', 'pglbutt', 'pglbutt')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        out, err, ret = run_spag('get', '/auth', '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        out, err, ret = run_spag('get', '/params?foo=bar&bar=@token&pglbutt=@[].pglbutt',
                                 '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {'foo': 'bar',
                                           'bar': 'abcde',
                                           'pglbutt': 'pglbutt'})

    def test_invalid_request_params(self):
        out, err, ret = run_spag('get', '/params?foo=bar&bar', '-e', ENDPOINT)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {'foo': 'bar',
                                           'bar': ''})

class TestGet(BaseTest):

    def test_get_no_endpoint(self):
        out, err, ret = run_spag('get', '/auth')
        self.assertNotEqual(ret, 0)
        self.assertEqual(err, 'Endpoint not set\n')

    def test_get_supply_endpoint(self):
        out, err, ret = run_spag('get', '/auth', '-e', ENDPOINT)
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"token": "abcde"})

    def test_get_presupply_endpoint(self):
        out, err, ret = run_spag('env', 'set', 'endpoint', ENDPOINT)
        self.assertEqual(out, '---\n"endpoint": "{0}"\n'.format(ENDPOINT))
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        out, err, ret = run_spag('get', '/things')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"things": []})

    def test_with_non_responsive_endpoint(self):
        out, err, ret = run_spag('env', 'set', 'endpoint', ENDPOINT)
        out, err, ret = run_spag('get', '/things', '-e', 'http://localhost:poo')
        self.assertEqual(ret, 1)
        self.assertEqual(err, 'Couldn\'t connect to server\n')

    def test_verbose_flag(self):
        out, err, ret = run_spag('get', '/auth', '-v', '-e', ENDPOINT,
                                 '-H', 'Content-type: application/json',
                                 '-H', 'Accept: application/json',
                                 '-H', 'mini: wumbo')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        prefix = textwrap.dedent("""
            -------------------- Request ---------------------
            GET http://localhost:5000/auth
            Accept: application/json
            Content-Type: application/json
            mini: wumbo
            Body:

            -------------------- Response ---------------------
            Status code 200
            content-length: 22
            """).strip()
        suffix = textwrap.dedent("""
            Body:
            {
              "token": "abcde"
            }
            """).strip()
        self.assertEqual(out.strip()[:len(prefix)], prefix)
        self.assertEqual(out.strip()[-len(suffix):], suffix)

    def test_get_non_formatted_json(self):
        out, err, ret = run_spag('get', '/rawjson', '-e', ENDPOINT)
        self.assertEqual(ret, 0)
        self.assertEqual(out, '{\n  "foo": "bar"\n}\n')
        self.assertEqual(json.loads(out), {"foo": "bar"})

class TestPost(BaseTest):

    def test_spag_post(self):
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
        out, err, ret = run_spag('post', '/things', '--data', '{"id": "a"}',
                                 '-H', 'content-type:application/json')
        self.assertEquals(ret, 0)
        self.assertEquals(json.loads(out), {"id": "a"})
        self.assertEquals(err, '')

class TestPut(BaseTest):

    def test_spag_put(self):
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
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
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
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
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
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
        run_spag('env', 'set', 'endpoint', ENDPOINT)
        run_spag('env', 'set', 'dir', RESOURCES_DIR)

    def test_spag_request_get(self):
        for command in ('r', 'request'):
            for name in ('auth.yml', 'auth'):
                out, err, ret = run_spag(command, name)
                self.assertEqual(err, '')
                self.assertEqual(ret, 0)
                self.assertEqual(json.loads(out), {"token": "abcde"})

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

    def test_spag_request_ls_w_absolute_dir(self):
        abspath = os.path.abspath(RESOURCES_DIR)
        _, err, ret = run_spag('env', 'set', 'dir', abspath)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('request', 'ls')
        self._check_spag_request_ls(*run_spag('request', 'ls'))

    def test_spag_request_ls_w_relative_dir(self):
        relpath = os.path.relpath(RESOURCES_DIR)
        _, err, ret = run_spag('env', 'set', 'dir', relpath)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self._check_spag_request_ls(*run_spag('request', 'ls'))

    def _check_spag_request_ls(self, out, err, ret):
        def parse(text):
            return text.split()
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

    def test_spag_cat_request(self):
        out, err, ret = run_spag('request', 'cat', 'auth.yml')
        self.assertEqual(err, '')
        self.assertEqual(out.strip(),
            textwrap.dedent("""
            method: GET
            uri: /auth
            headers:
                Accept: "application/json"
            """).strip())
        self.assertEqual(ret, 0)

class TestSpagEnvironments(BaseTest):

    def setUp(self):
        super(TestSpagEnvironments, self).setUp()
        run_spag('env', 'unset', '--everything')
        run_spag('env', 'deactivate')
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
        run_spag('env', 'set', 'dir=%s' % RESOURCES_DIR)

    def test_spag_environment_crud(self):
        out, err, ret = run_spag('env', 'set', 'endpoint', 'abcdefgh')
        self.assertIn('\"endpoint\": \"abcdefgh\"', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'cat')
        self.assertIn('\"endpoint\": \"abcdefgh\"', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'unset', '--everything')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'cat')
        self.assertEqual(out, '---\n{}\n')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

    def test_spag_environment_activate_deactivate(self):
        out, err, ret = run_spag('env', 'unset', '--everything')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'set', 'endpoint', 'abcdefgh')
        self.assertIn('\"endpoint\": \"abcdefgh\"', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'deactivate')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('env', 'cat')
        self.assertIn('\"endpoint\": \"abcdefgh\"', out)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

    def test_spag_set_environment_failure(self):
        out, err, ret = run_spag('env', 'set')
        self.assertIn('Invalid arguments.', err)
        self.assertNotEqual(ret, 0)

    def test_set_endoint_and_header(self):
        out, err, ret = run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT, 'headers.pglbutt', 'pglbutt')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertIn('headers', out)
        out, err, ret = run_spag('get', '/headers')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"Pglbutt": "pglbutt"})

    def test_spag_environment_activate_bad_env(self):
        out, err, ret = run_spag('env', 'activate', 'ninnymuggins')
        self.assertEqual(err, 'Tried to activate non-existent environment "ninnymuggins"\n')
        self.assertEqual(ret, 1)

    def test_spag_env_ls(self):
        # create some environment files
        def touch(filename):
            with open(filename, 'w') as f:
                f.write("{}")
            self.addCleanup(rm_file, filename)

        touch(".spag/environments/1.yml")
        touch(".spag/environments/2.yml")
        touch(".spag/environments/3.yml")

        out, err, ret = run_spag('env', 'ls')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(out.strip(),
            textwrap.dedent("""
            .spag/environments/1.yml
            .spag/environments/2.yml
            .spag/environments/3.yml
            .spag/environments/default.yml
            """).strip())

class TestSpagRemembers(BaseTest):

    def setUp(self):
        super(TestSpagRemembers, self).setUp()
        run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)

    def test_spag_remembers_request(self):
        last_file = os.path.join(SPAG_REMEMBERS_DIR, 'last.yml')

        self.assertFalse(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertFalse(os.path.exists(last_file))

        _, err, ret = run_spag('request', 'v2/post_thing.yml',
                               '--dir', RESOURCES_DIR)
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertTrue(os.path.exists(last_file))

        last_data = yaml.load(open(last_file, 'r').read())

        # check the saved request data
        req = last_data['request']
        self.assertEqual(set(req.keys()),
            set(['body', 'endpoint', 'uri', 'headers', 'method']))
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['endpoint'], ENDPOINT)
        self.assertEqual(req['uri'], '/things')
        self.assertEqual(req['headers']['Accept'], 'application/json')
        self.assertEqual(json.loads(req['body']), {"id": "c"})

        # check the saved response data
        resp = last_data['response']
        self.assertEqual(set(resp.keys()), set(['body', 'headers', 'status']))
        self.assertEqual(resp['headers']['content-type'], 'application/json')
        self.assertEqual(resp['status'], '201')
        self.assertEqual(json.loads(resp['body']), {"id": "c"})

    def test_spag_remembers_request_w_remember_as_flag(self):
        # Test that a request is remembered as last.yml and other.yml if we use
        # the flag `--remember-as other`
        last_file = os.path.join(SPAG_REMEMBERS_DIR, 'last.yml')
        other_file = os.path.join(SPAG_REMEMBERS_DIR, 'other.yml')

        self.assertFalse(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertFalse(os.path.exists(other_file))
        self.assertFalse(os.path.exists(last_file))

        _, err, ret = run_spag('request', 'v2/post_thing.yml',
                               '--dir', RESOURCES_DIR,
                               '--remember-as', 'other')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(SPAG_REMEMBERS_DIR))
        self.assertTrue(os.path.exists(other_file))

        other_data = yaml.load(open(other_file, 'r').read())
        last_data = yaml.load(open(last_file, 'r').read())
        self.assertEqual(other_data, last_data)

        # check the saved request data
        req = other_data['request']
        self.assertEqual(set(req.keys()),
            set(['body', 'endpoint', 'uri', 'headers', 'method']))
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['endpoint'], ENDPOINT)
        self.assertEqual(req['uri'], '/things')
        self.assertEqual(req['headers']['Accept'], 'application/json')
        self.assertEqual(json.loads(req['body']), {"id": "c"})

        # check the saved response data
        resp = other_data['response']
        self.assertEqual(set(resp.keys()), set(['body', 'headers', 'status']))
        self.assertEqual(resp['headers']['content-type'], 'application/json')
        self.assertEqual(resp['status'], '201')
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
        # filename = "{0}.yml".format(method)
        filename = "last.yml"
        filepath = os.path.join(SPAG_REMEMBERS_DIR, filename)

        self.assertFalse(os.path.exists(filepath))

        out, err, ret = run_spag(method, '/poo', '--data', '{"id": "1"}')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(filepath))

class TestSpagTemplate(BaseTest):

    def setUp(self):
        super(TestSpagTemplate, self).setUp()
        assert run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)[2] == 0
        assert run_spag('env', 'set', 'dir', '%s' % TEMPLATES_DIR)[2] == 0

    def _post_thing(self, thing_id):
        """post a thing to set last.response.body.id"""
        out, err, ret = run_spag('post', '/things', '--data',
                                 '{"id": "%s"}' % thing_id,
                                 '-H', 'Content-type: application/json',
                                 '-H', 'Accept: application/json')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": thing_id})
        self.assertEqual(ret, 0)

    def test_spag_template_with_keyword(self):
        out, err, ret = run_spag('request', 'templates/post_thing',
                                 '--with', 'thing_id', 'wumbo')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "wumbo"})
        self.assertEqual(ret, 0)

    def test_spag_template_with_keyword_short_flag(self):
        out, err, ret = run_spag('request', 'templates/post_thing',
                                 '-w', 'thing_id', 'wumbo')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "wumbo"})
        self.assertEqual(ret, 0)

    def test_spag_template_no_value_given(self):
        out, err, ret = run_spag('request', 'templates/post_thing')
        self.assertEqual(err, 'Failed to substitute for {{ thing_id }}\n')
        self.assertEqual(out, '')
        self.assertEqual(ret, 1)

    def test_spag_template_empty_value(self):
        # we're allowed to substitute an empty string
        out, err, ret = run_spag('request', 'templates/post_thing',
                                 '--with', 'thing_id', '')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": ""})
        self.assertEqual(ret, 0)

    def test_spag_template_multiple_with_keywords(self):
        out, err, ret = run_spag('request', 'templates/headers',
                                 '--with', 'hello', 'hello world',
                                 '--with', 'body_id', 'poo',
                                 '--with', 'thingy', 'my thing')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out),
            { "Body-Id": "poo",
              "Hello": "hello world",
              "Thingy": "my thing"  })
        self.assertEqual(ret, 0)

    def test_spag_template_alternative_items(self):
        # post a thing to set last.response.body.id
        self._post_thing('abcde')

        # the body-id in headers.yml is filled in using last.response.body.id
        # thingy is filled in using 'thingy2' instead of 'thingy'
        out, err, ret = run_spag('request', 'templates/headers',
                                 '--with', 'hello', 'hello world',
                                 '--with', 'thingy2', 'scooby doo')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out),
            { "Body-Id": "abcde",
              "Hello": "hello world",
              "Thingy": "scooby doo" })
        self.assertEqual(ret, 0)

    def test_spag_template_alternative_items_with_overrides(self):
        # post a thing to set last.response.body.id
        self._post_thing('abcde')

        # we want to see that the body-id is taken from the --with arg and not
        # from last.response.body.id
        out, err, ret = run_spag('request', 'templates/headers',
                                 '--with', 'hello', 'hello world',
                                 '--with', 'body_id', 'wumbo',
                                 '--with', 'thingy2', 'scooby doo')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out),
            { "Body-Id": "wumbo",
              "Hello": "hello world",
              "Thingy": "scooby doo" })
        self.assertEqual(ret, 0)

    def test_spag_template_shortshortcut(self):
        # post a thing to set last.response.body.id
        self._post_thing('wumbo')

        out, err, ret = run_spag('get', '/things/@id')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "wumbo"})
        self.assertEqual(ret, 0)

    def test_spag_template_shortcut(self):
        # post a thing to set last.response.body.id
        self._post_thing('wumbo')

        out, err, ret = run_spag('get', '/things/@body.id')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "wumbo"})
        self.assertEqual(ret, 0)

    def test_spag_template_default(self):
        self._post_thing('mydefaultid')

        # with no --with args given, the get_default template should
        # default to "mydefaultid"
        out, err, ret = run_spag('request', 'templates/get_default')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "mydefaultid"})
        self.assertEqual(ret, 0)

    def test_spag_template_shortcut_in_with(self):
        _, err, ret = run_spag('env', 'set', 'poke', 'pika')
        out, err, ret = run_spag('request', 'templates/post_thing',
                                 '--with', 'thing_id', '@[default].poke')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "pika"})
        self.assertEqual(ret, 0)

    def test_spag_template_shortcut_in_data(self):
        _, err, ret = run_spag('env', 'set', 'poke', 'pika')
        out, err, ret = run_spag('post', '/things',
                                 '--data', '{"id": "@[default].poke"}',
                                 '-H', 'Content-type: application/json',
                                 '-H', 'Accept: application/json')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "pika"})
        self.assertEqual(ret, 0)

    def test_spag_template_shortcut_in_header(self):
        _, err, ret = run_spag('env', 'set', 'poke', 'pika')
        out, err, ret = run_spag('get', '/headers', '-H', 'Poke: @[].poke')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"Poke": "pika"})
        self.assertEqual(ret, 0)

    def test_spag_template_from_default_and_active_environments(self):
        _, err, ret = run_spag('env', 'set',
                               'mini', 'barnacle boy',
                               'wumbo', 'mermaid man',
                               'thing', 'scooby doo')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('request', 'templates/get_default_env.yml')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out),
            { "Mini": "barnacle boy",
              "Wumbo": "mermaid man",
              "Thing": "scooby doo" })
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('request', 'templates/get_active_env.yml')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out),
            { "Mini": "barnacle boy",
              "Wumbo": "mermaid man",
              "Thing": "scooby doo" })
        self.assertEqual(ret, 0)

    def test_spag_template_shortcut_from_default_environment(self):
        _, err, ret = run_spag('request', 'templates/post_thing',
                               '--with', 'thing_id', 'wumbo')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        # set thing_id and lookup thing_id in the env using shortcut syntax
        run_spag('env', 'set', 'thing_id', 'wumbo')
        out, err, ret = run_spag('get', '/things/@[default].thing_id')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), { "id": "wumbo" })
        self.assertEqual(ret, 0)

    def test_spag_template_list_indexing(self):
        # setup the last request to have a list in it
        self._post_thing('mini')
        _, err, ret = run_spag('get', '/things')

        out, err, ret = run_spag('get', '/things/@body.things.0.id')
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out), {"id": "mini"})
        self.assertEqual(ret, 0)

    def test_spag_template_list_index_out_of_bounds(self):
        # setup the last request to have a list in it
        self._post_thing('mini')
        _, err, ret = run_spag('get', '/things')

        out, err, ret = run_spag('get', '/things/@body.things.1.id')
        self.assertEqual(err.strip(), 'Failed to substitute for {{ last.response.body.things.1.id }}')
        self.assertEqual(ret, 1)

    def test_spag_template_list_w_invalid_index(self):
        # setup the last request to have a list in it
        self._post_thing('mini')
        _, err, ret = run_spag('get', '/things')

        out, err, ret = run_spag('get', '/things/@body.things.poo.id')
        self.assertIn(err.strip(), 'Failed to substitute for {{ last.response.body.things.poo.id }}')
        self.assertEqual(ret, 1)

    def test_spag_templated_env_set(self):
        # set a value we'll refer to in a template parameter
        out, err, ret = run_spag('env', 'set', 'squidward', 'tentacle')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(yaml.load(out).get('squidward'), 'tentacle')

        # check we can use template params when setting headers in the env
        out, err, ret = run_spag('env', 'set', 'headers.sandy', '@[].squidward')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(yaml.load(out)['headers'].get('sandy'), 'tentacle')

    def test_verbose_flag(self):
        out, err, ret = run_spag('request', 'post_thing', '-v',
                                 '--with', 'thing_id', 'wumbo')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        prefix = textwrap.dedent("""
            -------------------- Request ---------------------
            POST http://localhost:5000/things
            Accept: application/json
            Content-Type: application/json
            Body:
            {
              "id": "wumbo"
            }
            -------------------- Response ---------------------
            Status code 201
            content-length: 19
            content-type: application/json
            """).strip()
        suffix = textwrap.dedent("""
            Body:
            {
              "id": "wumbo"
            }
            """).strip()
        self.assertEqual(out.strip()[:len(prefix)], prefix)
        self.assertEqual(out.strip()[-len(suffix):], suffix)

    def test_spag_template_w_remember_as_flag(self):
        out, err, ret = run_spag('request', 'post_thing', '-v',
                                 '--with', 'thing_id', 'wumbo',
                                 '--remember-as', 'wumbo')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('get', '/things/{{wumbo.response.body.id}}')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEquals(json.loads(out), {"id": "wumbo"})

    def test_error_using_shortcut_syntax_inside_template_list(self):
        out, err, ret = run_spag('get', '/things/{{a, @id}}')
        self.assertEqual(err.strip(), "Invalid character '@' found in template item")
        self.assertEqual(ret, 1)
        self.assertEqual(out, '')

    def test_shortcut_syntax_allows_underscores_and_dashes(self):
        out, err, ret = run_spag('env', 'set', '_my-wumbo_', 'mini')
        self.assertEqual((err, ret), ('', 0))

        out, err, ret = run_spag('request', 'post_thing',
                                 '--with', 'thing_id', '@[]._my-wumbo_')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(json.loads(out), {"id": "mini"})

    def test_error_message_on_empty_list(self):
        _, err, _ = run_spag('get', '/things/{{}}')
        self.assertEqual(err.strip(),
            "Expected a template list item, but found the end of the list '}}'")

    def test_error_message_on_unclosed_list(self):
        eof_msg = "Expected a template list item, but found eof"
        _, err, _ = run_spag('get', '/things/{{')
        self.assertEqual(err.strip(), eof_msg)

        _, err, _ = run_spag('get', '/things/@')
        self.assertEqual(err.strip(), eof_msg)

    def test_error_message_on_missing_list_item(self):
        _, err, _ = run_spag('get', '/things/@:')
        self.assertEqual(err.strip(), "Expected a template list item, but found ':'")

        _, err, _ = run_spag('get', '/things/@ :')
        self.assertEqual(err.strip(), "Expected a template list item, but found ':'")

        _, err, _ = run_spag('get', '/things/{{ : ')
        self.assertEqual(err.strip(), "Expected a template list item, but found ':'")

        _, err, _ = run_spag('get', '/things/@,')
        self.assertEqual(err.strip(), "Expected a template list item, but found ','")

        _, err, _ = run_spag('get', '/things/@ ,')
        self.assertEqual(err.strip(), "Expected a template list item, but found ','")

        _, err, _ = run_spag('get', '/things/{{ : ')
        self.assertEqual(err.strip(), "Expected a template list item, but found ':'")

    def test_error_message_on_invalid_list_item(self):
        _, err, _ = run_spag('get', '/things/{{/}} ')
        self.assertEqual(err.strip(), "Invalid character '/' found in template item")

        _, err, _ = run_spag('get', '/things/@/')
        self.assertEqual(err.strip(), "Invalid character '/' found in template item")

    def test_inspect(self):
        out, err, ret = run_spag('request', 'inspect', 'show_params_test')
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)
        self.assertEqual(out.strip(),
            textwrap.dedent("""
            {{ tenant, [].tenant, [myenv].tenant: noauth-project }} needs one of
                * flag "--with tenant <value>"
                * key ["tenant"] from the active environment
                * key ["tenant"] from environment "myenv"
                * defaults to "noauth-project" if no matches are found
            {{ last.response.body.id, other.response.body.id }} needs one of
                * key ["response", "body", "id"] from the previous request
                * key ["response", "body", "id"] from the request saved as "other"
            """).strip())

class TestSpagHistory(BaseTest):

    def setUp(self):
        super(TestSpagHistory, self).setUp()
        _, _, ret = run_spag('env', 'set', 'endpoint', '%s' % ENDPOINT)
        _, _, ret = run_spag('env', 'set', 'dir', '%s' % TEMPLATES_DIR)
        self.assertEqual(ret, 0)

    def test_empty_history(self):
        out, err, ret = run_spag('history')

        self.assertEqual(err, '')
        self.assertEqual(out.strip(), '')
        self.assertEqual(ret, 0)

    def _run_test_method_history(self, spag_call, expected):
        _, err, ret = spag_call()
        self.assertEqual(err, '')
        self.assertEqual(ret, 0)

        out, err, ret = run_spag('history')
        self.assertEqual(err, '')
        self.assertEqual(out, expected)

    def test_post_method_history(self):
        self._run_test_method_history(
            lambda: run_spag('post', '/things', '-d', '{"id": "posty"}'),
            expected='0: POST %s/things\n' % ENDPOINT)

    def test_put_method_history(self):
        self._run_test_method_history(
            lambda: run_spag('put', '/things/id'),
            expected='0: PUT %s/things/id\n' % ENDPOINT)

    def test_patch_method_history(self):
        self._run_test_method_history(
            lambda: run_spag('patch', '/things/id'),
            expected='0: PATCH %s/things/id\n' % ENDPOINT)

    def test_get_method_history(self):
        self._run_test_method_history(
            lambda: run_spag('get', '/things/wumbo'),
            expected='0: GET %s/things/wumbo\n' % ENDPOINT)

    def test_delete_method_history(self):
        self._run_test_method_history(
            lambda: run_spag('delete', '/things/wumbo'),
            expected='0: DELETE %s/things/wumbo\n' % ENDPOINT)

    def test_spag_history_show_index(self):
        # Make a request
        _, err, _ = run_spag('get', '/things')

        # check 'spag history <index>'
        out, err, ret = run_spag('history', '0')
        self.assertEqual(err, '')
        self.assertIn('GET %s/things' % ENDPOINT, out)
        self.assertEqual(ret, 0)

    def test_spag_history_show_index_invalid_id(self):
        # Make a request
        _, err, _ = run_spag('get', '/things')

        # Request an invalid ID
        out, err, ret = run_spag('history', '9')
        self.assertEqual(err, 'No request at #9\n')
        self.assertNotEqual(ret, 0)

    def test_multi_history_items(self):
        # make three requests
        _, err, _ = run_spag('get', '/things')
        self.assertEqual(err, '')
        _, err, _ = run_spag('post', '/things',
                             '-d', '{"id": "wumbo"}')
        self.assertEqual(err, '')
        _, err, _ = run_spag('get', '/things/wumbo')
        self.assertEqual(err, '')

        # check `spag history`
        out, err, ret = run_spag('history')
        self.assertEqual(err, '')
        self.assertEqual(out,
            "0: GET {0}/things/wumbo\n"
            "1: POST {0}/things\n"
            "2: GET {0}/things\n"
            .format(ENDPOINT))
        self.assertEqual(ret, 0)

        # check 'spag history <index>'
        out, err, ret = run_spag('history', '1')
        self.assertEqual(err, '')
        self.assertIn('POST %s/things' % ENDPOINT, out)
        self.assertEqual(ret, 0)

    def test_history_and_requests(self):
        # make three requests
        _, err, _ = run_spag('get', '/things')
        self.assertEqual(err, '')
        _, err, _ = run_spag('request', 'templates/post_thing',
                             '--with', 'thing_id', 'wumbo')
        self.assertEqual(err, '')
        _, err, _ = run_spag('get', '/things/')
        self.assertEqual(err, '')

        # check `spag history`
        out, err, ret = run_spag('history')
        self.assertEqual(err, '')
        self.assertEqual(out,
            "0: GET {0}/things/\n"
            "1: POST {0}/things\n"
            "2: GET {0}/things\n"
            .format(ENDPOINT))
        self.assertEqual(ret, 0)

        # check 'spag history <index>'
        out, err, ret = run_spag('history', '1')
        self.assertEqual(err, '')
        self.assertIn('POST %s/things' % ENDPOINT, out)
        self.assertEqual(ret, 0)
