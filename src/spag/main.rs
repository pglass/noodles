extern crate curl;
extern crate docopt;

use curl::http::handle::Method;
use curl::http;
use docopt::Docopt;
use super::request::SpagRequest;
use super::file;

docopt!(Args derive Debug, "
Usage:
    spag (-h|--help)
    spag env set (<key> <val>)...
    spag env show [<environment>]
    spag (get|post|put|patch|delete) <resource> [(-H <header>)...]
    spag request <file> [(-H <header>)...]
    spag request show <file>
    spag history
    spag history show <index>

Options:
    -h, --help      Show this message
    -H, --header    Supply a header

Arguments:
    <resource>      The path of an api resource, like /v2/things
    <header>        An http header, like 'Content-type: application/json'
    <environment>   The name of an environment, like 'default'
    <index>         An index, starting at zero

Commands:
    env set         Set a key-value pair in the active environment
    env show        Print out the specified environment
    get             An HTTP GET request
    post            An HTTP POST request
    put             An HTTP PUT request
    patch           An HTTP PATCH request
    delete          An HTTP DELETE request
    request         Make a request using a predefined file
    request show    Show the specified request file
    history         Print a list of previously made requests
    history show    Print out a previous request by its index
");

pub fn main() {
    let args: Args = Args::docopt().decode().unwrap_or_else(|e| e.exit());
    println!("{:?}", args);

    if args.cmd_request {
        spag_request(&args);
    } else if args.cmd_history {
        spag_history(&args);
    } else if args.cmd_env {
        spag_env(&args);
    } else if args.cmd_get || args.cmd_post || args.cmd_put || args.cmd_patch || args.cmd_delete {
        spag_method(&args);
    }
}

fn spag_env(args: &Args) {
    if args.cmd_show {
        spag_env_show(&args);
    } else if args.cmd_set {
        spag_env_set(&args);
    } else {
        panic!("BUG: Invalid command");
    }
}

fn spag_env_set(args: &Args) {
    println!("TODO");
    let y = file::load_yaml_file("active.yml");
    println!("{:?}", y);
}

fn spag_env_show(args: &Args) {
    let s = file::read_file("active.yml");
    println!("{}", s.trim());
}

fn spag_history(args: &Args) {
    println!("called spag history");
}

fn spag_request(args: &Args) {
    println!("called spag request");
}

fn spag_method(args: &Args) {
    let method = get_method_from_args(args);
    let endpoint = "http://localhost:5000".to_string();
    let uri = args.arg_resource.to_string();
    let mut req = SpagRequest::new(method, endpoint, uri);
    req.add_headers(args.arg_header.iter());
    do_request(&req);
}

fn do_request(req: &SpagRequest) {
    println!("{:?}", req);
    let mut handle = http::handle();
    let resp = req.prepare(&mut handle).exec().unwrap();
    println!("{}", resp);
}

fn get_method_from_args(args: &Args) -> Method {
    if args.cmd_get { Method::Get }
    else if args.cmd_post { Method::Post }
    else if args.cmd_put { Method::Put }
    else if args.cmd_patch { Method::Patch }
    else if args.cmd_delete { Method::Delete }
    else { panic!("BUG: method not recognized"); }
}
