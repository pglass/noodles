#!/usr/bin/env python

import os
import sys
import json
import functools

import click
import requests
import yaml

import spag_files
from spag_remembers import SpagRemembers
from common import ToughNoodles

class Environment(object):

    ENV_FILE = '.spag.env'
    @classmethod
    def get(cls):
        if os.path.exists(cls.ENV_FILE):
            with click.open_file(cls.ENV_FILE, 'r') as f:
                return yaml.load(f)
        else:
            raise ToughNoodles("Endpoint not set")

    @classmethod
    def set(cls, **kwargs):
        # This ignores any arguments that are set to None
        kwargs = {key: value for key, value in kwargs.items() if value is not None}

        if os.path.exists(cls.ENV_FILE):
            f = click.open_file(cls.ENV_FILE, 'r')
            data = yaml.load(f)
            data.update(kwargs)
        else:
            data = kwargs

        f = click.open_file(cls.ENV_FILE, 'w+')
        yaml.safe_dump(data, f, default_flow_style=False)
        return data

    @classmethod
    def clear(cls):
        if os.path.exists(cls.ENV_FILE):
            os.remove(cls.ENV_FILE)

def determine_endpoint(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if kwargs['endpoint'] is None:
            try:
                endpoint = Environment.get()['endpoint']
                kwargs['endpoint'] = endpoint
            except ToughNoodles as e:
                click.echo(str(e), err=True)
                sys.exit(1)
        return f(*args, **kwargs)
    return wrapper

def prepare_headers(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        header = kwargs['header']
        if header is None or header == ():
            try:
                headers = Environment.get()['headers']
                kwargs['header'] = headers
            except ToughNoodles:
                kwargs['header'] = None
            except KeyError:
                kwargs['header'] = None
        else:
            try:
                # Headers come in as a tuple ('Header:Content', 'Header:Content')
                kwargs['header'] = {key: value for (key, value) in [h.split(':') for h in header]}
            except ValueError:
                click.echo("Error: Invalid header!", err=True)
                sys.exit(1)

        return f(*args, **kwargs)
    return wrapper

def common_request_args(f):
    @click.option('--endpoint', '-e', metavar='<endpoint>',
                  default=None, help='Manually override the endpoint')
    @click.option('--header', '-H', metavar = '<header>', multiple=True,
                  default=None, help='Header in the form Key:Value')
    @click.option('--show-headers', '-h', is_flag=True,
                  help='Prints the headers along with the response body')
    @click.option('--data', '-d', required=False, help='the request data')
    @determine_endpoint
    @prepare_headers
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


@click.group()
@click.version_option()
def cli():
    """Spag.

    This is the spag http client. It's spagtacular.
    """

@cli.command('set')
@click.argument('endpoint', default=None, required=False)
@click.option('--header', '-H', metavar = '<header>', multiple=True,
              default=None, help='Header in the form key:value')
@prepare_headers
def spag_set(endpoint=None, header=None):
    """Set the endpoint and/or headers."""
    if endpoint is None and header == None:
        click.echo("Error: You must provide something to set!", err=True)
        sys.exit(1)

    # This should be expandable to future environment variables
    kwargs = {'endpoint': endpoint, 'headers': header}
    try:
        e = Environment.set(**kwargs)
        for key, value in e.items():
            click.echo("%s: %s" % (key, value))
    except ToughNoodles as e:
        click.echo(str(e), err=True)
        sys.exit(1)

@cli.command('show')
def spag_show():
    """Show the endpoint."""
    try:
        env = Environment.get()
        for key, value in env.items():
            click.echo("%s: %s" % (key, value))
    except ToughNoodles as e:
        click.echo(str(e), err=True)
        sys.exit(1)

@cli.command('clear')
def spag_clear():
    """Clear the endpoint."""
    try:
        Environment.clear()
        click.echo("Endpoint cleared.")
    except ToughNoodles as e:
        click.echo(str(e), err=True)
        sys.exit(1)

def show_response(resp, show_headers):
    if show_headers:
        for k, v in resp.headers.items():
            click.echo("{0}: {1}".format(k, v))
    click.echo(resp.text)

@cli.command('get')
@click.argument('resource')
@common_request_args
def get(resource, endpoint=None, data=None, header=None, show_headers=False):
    """HTTP GET"""
    uri = endpoint + resource
    r = requests.get(uri, headers=header, data=data)
    show_response(r, show_headers)
    SpagRemembers.remember_request('get', r)

@cli.command('post')
@click.argument('resource')
@common_request_args
def post(resource, endpoint=None, data=None, header=None, show_headers=False):
    """HTTP POST"""
    uri = endpoint + resource
    r = requests.post(uri, data=data, headers=header)
    show_response(r, show_headers)
    SpagRemembers.remember_request('post', r)

@cli.command('put')
@click.argument('resource')
@common_request_args
def put(resource, endpoint=None, data=None, header=None, show_headers=False):
    """HTTP PUT"""
    uri = endpoint + resource
    r = requests.put(uri, data=data, headers=header)
    show_response(r, show_headers)
    SpagRemembers.remember_request('put', r)

@cli.command('patch')
@click.argument('resource')
@common_request_args
def patch(resource, endpoint=None, data=None, header=None, show_headers=False):
    """HTTP PATCH"""
    uri = endpoint + resource
    r = requests.patch(uri, data=data, headers=header)
    show_response(r, show_headers)
    SpagRemembers.remember_request('patch', r)

@cli.command('delete')
@click.argument('resource')
@common_request_args
def delete(resource, endpoint=None, data=None, header=None, show_headers=False):
    """HTTP DELETE"""
    uri = endpoint + resource
    r = requests.delete(uri, data=data, headers=header)
    show_response(r, show_headers)
    SpagRemembers.remember_request('delete', r)


@cli.command('request')
@click.argument('name', required=False)
@common_request_args
# TODO: set dir in the environment, and then required=False
@click.option('--dir', required=True,
              help='the dir to search for request files')
@click.option('--show', required=False, is_flag=True,
              help='show request file, or show all request files if no name')
def request(dir, name=None, endpoint=None, data=None, header=None,
            show_headers=False, show=False):
    try:
        if show and name is None:
            for x in spag_files.SpagFilesLookup(dir).get_file_list():
                click.echo(x)
        elif show:
            filename = spag_files.SpagFilesLookup(dir).get_path(name)
            filename = os.path.relpath(filename, '.')
            click.echo("File {0}".format(filename))
            with click.open_file(filename, 'r') as f:
                click.echo(f.read())
            # maybe should we still perform the request?
        else:
            filename = spag_files.SpagFilesLookup(dir).get_path(name)

            # load the request data into a dict
            req = spag_files.load_file(filename)
            kwargs = {
                'url': endpoint + req['uri'],
                'headers': header or req.get('headers', {})
            }
            if data is not None:
                kwargs['data'] = data
            elif 'body' in req:
                kwargs['data'] = req['body']

            # I don't know how to call click-decorated get(), post(), etc functions
            # Use requests directly instead
            method = req['method'].lower()
            resp = getattr(requests, method)(**kwargs)
            show_response(resp, show_headers)

            SpagRemembers.remember_request(name, resp)
    except ToughNoodles as e:
        click.echo(str(e), err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()
