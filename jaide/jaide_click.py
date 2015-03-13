#!/usr/bin/env python
""" Jaide CLI script for manipulating Junos devices.

This is the cli script that is a base use case of the jaide module.
It is a command line tool, able to be used with the 'jaide' command that is
installed along with the jaide package. It allows for communicating with,
manipulating, and retrieving data from Junos based devices.

For expansive information on the Jaide class, and the jaide CLI tool,
refer to the readme file or the associated examples/documentation. More
information can be found at the github page:

https://github.com/NetworkAutomation/jaide
"""
# standard modules
from os import path
import multiprocessing
import re
# intra-Jaide imports
import wrap
from utils import clean_lines
from color_utils import secho
# non-standard modules:
import click

# needed for '-h' to be a help option
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

# TODO: --compare argument for doing just comparison without commit checking.
# TODO: Verbosity argument for seeing more/less output?
# TODO: related to above, maybe --quiet to show nothing?


class AliasedGroup(click.Group):

    """ Extends click.Group to allow for partial commands. """

    def get_command(self, ctx, cmd_name):
        """ Allow for partial commands. """
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Command ambiguous, could be: %s' %
                 ', '.join(sorted(matches)))


@click.pass_context
def write_validate(ctx, param, value):
    """ Validate the -w option. """
    if value != ("default", "default"):
        # Validate the -w option
        try:
            mode, dest_file = (value[0], value[1])
        except IndexError:
            raise click.BadParameter('Expecting two arguments, one for how to '
                                     'output (s, single, m, multiple), and '
                                     'the second is a filepath where to put'
                                     ' the output.')
        if mode.lower() not in ['s', 'single', 'm', 'multiple']:
            raise click.BadParameter('The first argument of the -w/--write '
                                     'option must specifies whether to write'
                                     ' to one file per device, or all device'
                                     ' output to a single file. Valid options'
                                     ' are "s", "single", "m", and "multiple"')
        ctx.obj['out'] = (mode.lower(), dest_file)
    else:
        ctx.obj['out'] = None


# TODO: add aliasing of commands to allow partial command names (also change command to operational) (click advanced patterns doc)
# TODO: can't change the name of prog from jaide_click.py in help text using click?
@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option('-i', '--ip', 'host', prompt="IP or hostname of Junos device",
              help="The target hostname(s) or IP(s). Can be a comma separated"
              " list, or path to a file listing devices on individual lines.")
@click.option('-u', '--username', prompt="Username")
@click.password_option('-p', '--password', prompt="Password")
@click.option('-P', '--port', default=22, help="The port to connect to. "
              "Defaults to SSH (22)")
@click.option('-t', '--session-timeout', type=click.IntRange(5, 7200),
              default=300, help="The session timeout value, in seconds, for"
              " declaring a lost session. Default is 300 seconds. This should"
              " be increased when no output could be seen for more than 5 "
              "minutes (ex. requesting a system snapshot).")
@click.option('-T', '--connect-timeout', type=click.IntRange(1, 60), default=5,
              help="The timeout, in seconds, for declaring a device "
              "unreachable during connection establishment. Default is 5"
              " seconds.")
@click.version_option(version='2.0.0', prog_name='jaide')
@click.option('-w', '--write', nargs=2, type=click.STRING, expose_value=False,
              callback=write_validate, help="Write the output to a file "
              "instead of echoing it to the terminal. This can be useful "
              "when touching more than one device, because the output can be "
              "split into a file per device. In this case, output filename "
              "format is IP_FILENAME.", metavar="[s | single | m | multiple]"
              " FILEPATH", default=("default", "default"))
@click.pass_context
def main(ctx, host, password, port, session_timeout, connect_timeout,
         username):
    """ Manipulate one or more Junos devices.

    Will connect to one or more Junos devices, and manipulate them based on
    the command you have chosen. If a comma separated list or a file
    containing IP/hostnames on each line is given for the IP option, the
    commands will be carried out simultaneously to each device.
    """
    ctx.obj['hosts'] = [ip for ip in clean_lines(host)]
    ctx.obj['conn'] = {
        "username": username,
        "password": password,
        "port": port,
        "session_timeout": session_timeout,
        "connect_timeout": connect_timeout
    }
    # function_translation = {
    #     "command": do_command
    # }
    # # grab all the IPs
    # ip_list = [ip for ip in clean_lines(host)]
    # function = function_translation[ctx.invoked_subcommand]
    # if len(ip_list) > 1:
    #     mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    #     # ctx.obj['hosts'] = {}
    #     for ip in ip_list:
    #         # ctx.obj['hosts'][ip] = open_connection(ctx, ip, username, password,
    #         #                                        connect_timeout,
    #         #                                        session_timeout, port, function)
    #         # mp_pool.apply_async(function_translation[ctx.invoked_subcommand],
    #         #                     args=(ctx.obj['hosts'][ip], ctx.args))

    #         # TODO: got it working by making args a tuple, and pulling context object out, perhaps can go back to not needing do_command()?
    #         mp_pool.apply_async(open_connection, args=(ctx, ip, username, password, function, ctx.args[1:],
    #                             connect_timeout, session_timeout, port), callback=write_out)
    #         # open_connection(ctx, ip, username, password, function, ctx.args[1:],
    #         #                     connect_timeout, session_timeout, port)
    #     mp_pool.close()
    #     mp_pool.join()
    # else:
    #     write_out(open_connection(ctx, ip_list[0], username,
    #                               password, function, ctx.args[1:],
    #                               connect_timeout, session_timeout, port))
    # sys.exit()


def write_out(input):
    """ Callback function to write the output from the script.

        @param input: A tuple containing two things:
                    | 1. None or Tuple of file mode and destination filepath
                    | 2. The output to be dumped.
                    |
                    | If the first index of the tuple *is not* another tuple,
                    | the output will be written to sys.stdout. If the first
                    | index *is* a tuple, that tuple is further broken down
                    | into the mode (single file or one file for each IP),
                    | and the destination filepath.
        @type input: tuple

        @returns: None
    """
    to_file, output = input
    try:
        mode, dest_file = to_file
    except TypeError:
        click.echo(output)
    else:
        ip = output.split('device: ')[1].split('\n')[0].strip()
        if mode in ['m', 'multiple']:
            # put the IP in front of the filename if we're writing each device
            # to its own file.
            dest_file = path.join(path.split(dest_file)[0], ip + "_" +
                                  path.split(dest_file)[1])
        try:
            out_file = open(dest_file, 'a+b')
        except IOError as e:
            secho("Could not open output file '%s' for writing. Output "
                  "would have been:\n%s" % (dest_file, output), 'error')
            secho('Here is the error for opening the output file:' + str(e),
                  'error')
        else:
            click.echo(output, nl=False, file=out_file)
            secho('%s output appended to: %s' % (ip, dest_file))
            out_file.close()


def at_time_validate(ctx, param, value):
    """ Callback validating the at_time commit option. """
    # if they are doing commit_at, ensure the input is formatted correctly.
    if value is not None:
        if (re.search(r'([0-2]\d)(:[0-5]\d){1,2}', value) is None and
            re.search(r'\d{4}-[01]\d-[0-3]\d [0-2]\d:[0-5]\d(:[0-5]\d)?',
                      value) is None):
            raise click.BadParameter("A commit at time must be in one of the "
                                     "two formats: 'hh:mm[:ss]' or "
                                     "'yyyy-mm-dd hh:mm[:ss]' (seconds are "
                                     "optional).")
    ctx.obj['at_time'] = value


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('commands', default='annotate system ""', required=True)
@click.option('--blank/--no-blank', default=False, help="Flag to indicate to"
              " make a commit with no changes. Defaults to False. Functionally"
              " this commits one set command: 'annotate system'")
@click.option('--check/--no-check', default=False, help="Flag to indicate to"
              " only do a commit check. Defaults to False.")
# TODO: compare only
# TODO: blank cannot work since commands are required. (maybe only SRX doesn't allow 'annotate system')
@click.option('--sync/--no-sync', default=False, help="Flag to indicate to"
              "make the commit synchronize between routing engines. Defaults"
              " to false.")
@click.option('-c', '--comment', help="Accepts a string to be commented in the"
              " system commit log.")
@click.option('-C', '--confirm', type=click.IntRange(60, 7200), help="Specify"
              " a commit confirmed timeout, **in seconds**. If the device "
              " does not receive another commit within the timeout, the "
              "changes will be rolled back. Allowed range is 60 to 7200 "
              "seconds.")
@click.option('-a', '--at', 'at_time', callback=at_time_validate,
              help="Specify the time at which the commit should occur. "
              "Can be in one of two formats: hh:mm[:ss]  or  yyyy-mm-dd "
              "hh:mm[:ss]")
@click.pass_context
def commit(ctx, commands, blank, check, sync, comment, confirm, at_time):
    """ Execute a commit against the device.

    This function will send set commands to a device, and commit
    the changes. Options exist for confirming, comments,
    synchronizing, checking, blank commits, or delaying to a later time/date.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param commands: String containing the set command to be sent to the
                   | device. It can be a python list of strings, a single set
                   | command, a comma separated string of commands, or a
                   | string filepath pointing to a file with set commands
                   | on each line.
    @type commands: str or list
    @param blank: A bool set to true to only make a blank commit. A blank
                | commit makes a commit, but doesn't have any set commands
                | associated with it, so no changes are made, but a commit
                | does happen.
    @type blank: bool
    @param check: A bool set to true to only run a commit check, and not
                | commit any changes. Useful for checking syntax of set
                | commands.
    @type check: bool
    @param sync: A bool set to true to sync the commit across both REs.
    @type sync: bool
    @param comment: A string that will be logged to the commit log
                  | describing the commit.
    @type comment: str
    @param confirm: An integer of seconds to commit confirm for.
    @type confirm: int
    @param at_time: A string containing the time or time and date of when
                  | the commit should happen. Junos is expecting one of two
                  | formats:
                  | A time value of the form hh:mm[:ss] (hours, minutes,
                  |     and optionally seconds)
                  | A date and time value of the form yyyy-mm-dd hh:mm[:ss]
                  |     (year, month, date, hours, minutes, and optionally
                  |      seconds)
    @type at_time: str

    @returns: The output from the device.
    @rtype: str
    """
    if not blank and commands == 'annotate system ""':
        raise click.BadParameter("--blank and the commands argument cannot"
                                 " both be omitted.")
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        write_out(wrap.open_connection(ip,
                  ctx.obj['conn']['username'],
                  ctx.obj['conn']['password'],
                  wrap.commit,
                  [commands, check, sync, comment, confirm,
                   ctx.obj['at_time'], blank],
                  ctx.obj['out'],
                  ctx.obj['conn']['connect_timeout'],
                  ctx.obj['conn']['session_timeout'],
                  ctx.obj['conn']['port'])
                  )
        # mp_pool.apply_async(wrap.open_connection, args=(ip,
        #                     ctx.obj['conn']['username'],
        #                     ctx.obj['conn']['password'],
        #                     wrap.commit,
        #                     [commands, check, sync, comment, confirm,
        #                      ctx.obj['at_time']],
        #                     ctx.obj['out'],
        #                     ctx.obj['conn']['connect_timeout'],
        #                     ctx.obj['conn']['session_timeout'],
        #                     ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('commands', required=True)
@click.pass_context
def compare(ctx, commands):
    """ Retrieve 'show | compare' output for set commands. """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.compare, [commands],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('source', type=click.Path())
@click.argument('destination', type=click.Path(resolve_path=True))
@click.option('--progress/--no-progress', default=False, help="Flag to show "
              "progress as the transfer happens. Defaults to False")
# TODO: will need to set ctx.obj['multi'] tracking multi devices to know if we're renaming the output file.
@click.pass_context
def pull(ctx, source, destination, progress):
    """ Copy file(s) from device -> local machine.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param source: the source filepath or dirpath
    @type source: str
    @param destination: the destination filepath or dirpath
    @type destination: str
    @param progress: bool set to True if we should request a progress callback
                   | from the Jaide object. Always set to False when
                   | we're copying to/from multiple devices.
    @type progress: bool

    @returns: the output from the copy operation
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.pull, [source, destination, progress],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('source', type=click.Path(exists=True, resolve_path=True))
@click.argument('destination', type=click.Path())
@click.option('--progress/--no-progress', default=False, help="Flag to show "
              "progress as the transfer happens. Defaults to False")
# TODO: will need to set ctx.obj['multi'] tracking multi devices to know if we're renaming the output file.
@click.pass_context
def push(ctx, source, destination, progress):
    """ Copy file(s) from local machine -> device.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param source: the source filepath or dirpath
    @type source: str
    @param destination: the destination filepath or dirpath
    @type destination: str
    @param progress: bool set to True if we should request a progress callback
                   | from the Jaide object. Always set to False when
                   | we're copying to/from multiple devices.
    @type progress: bool

    @returns: the output from the copy operation
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.push, [source, destination, progress],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('commands', required=True)
@click.option('-f', '--format', type=click.Choice(['text', 'xml']),
              default='text', help="The requested format of the response.")
@click.option('-x', '--xpath', required=False, help="An xpath expression"
              " that will filter the results. Forces response format xml."
              " Example: '//rt-entry'")
@click.pass_context
def operational(ctx, commands, format, xpath):
    """ Execute operational mode command(s).

    This function will send operational mode commands to a Junos
    device. jaide.utils.clean_lines() is used to determine how we are
    receiving commands, and ignore comment lines or blank lines in
    a command file.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param commands: The shell commands to send to the device. Can be one of
                   | four things:
                   |    1. A single shell command as a string.
                   |    2. A string of comma separated shell commands.
                   |    3. A python list of shell commands.
                   |    4. A filepath of a file with shell commands on each
                   |         line.
    @type commands: str
    @param format: String specifying what format to request for the
                 | response from the device. Defaults to 'text', but
                 | also accepts 'xml'.
    @type format: str
    @param xpath: An xpath expression on which we should filter the results.
                | This enforces 'xml' for the format of the response.
    @type xpath: str

    @returns: The output that should be shown to the user.
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.command, [commands, format, xpath],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(name='info', context_settings=CONTEXT_SETTINGS)
@click.pass_context
def device_info(ctx):
    """ Get basic device information.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.device_info, None,
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.option('-o', '--second-host', required=True, help="The second"
              " hostname or IP address to compare against.")
@click.option('-m', '--mode', type=click.Choice(['set', 'stanza']),
              default='set', help="How to view the differences. Can be"
              " either 'set' or 'stanza'. Defaults to 'set'")
@click.pass_context
def diff_config(ctx, second_host, mode):
    """ Config comparison between two devices.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param second_host: The IP/hostname of the second device to pull from
    @type second_host: str
    @param mode: The mode in which we are retrieving the config ('set' or
               | 'stanza')
    @type mode: str

    @returns: The config differences between the two devices.
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.diff_config, [second_host, mode],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(name="health", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def health_check(ctx):
    """ Get alarm and device health information.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context

    @returns: The output from the device, and any Jaide formatting help.
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.health_check, [],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(name="errors", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def interface_errors(ctx):
    """Get any interface errors from the device.

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context

    @returns: The output from the device, and any Jaide formatting help.
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.interface_errors, [],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument('commands', required=True)
@click.pass_context
def shell(ctx, commands):
    """ Send bash command(s) to the device(s).

    @param ctx: The click context paramter, for receiving the object dictionary
              | being manipulated by other previous functions. Needed by any
              | function with the @click.pass_context decorator.
    @type ctx: click.Context
    @param commands: The shell commands to send to the device. Can be one of
                   | four things:
                   |    1. A single shell command as a string.
                   |    2. A string of comma separated shell commands.
                   |    3. A python list of shell commands.
                   |    4. A filepath of a file with shell commands on each
                   |         line.
    @type commands: str or list

    @returns: The output from the device, and any Jaide formatting help.
    @rtype: str
    """
    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
    for ip in ctx.obj['hosts']:
        mp_pool.apply_async(wrap.open_connection, args=(ip,
                            ctx.obj['conn']['username'],
                            ctx.obj['conn']['password'],
                            wrap.shell, [commands],
                            ctx.obj['out'],
                            ctx.obj['conn']['connect_timeout'],
                            ctx.obj['conn']['session_timeout'],
                            ctx.obj['conn']['port']), callback=write_out)
    mp_pool.close()
    mp_pool.join()


def run():
    main(obj={})

if __name__ == '__main__':
    run()
