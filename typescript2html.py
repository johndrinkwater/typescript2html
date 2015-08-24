#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
    typescript2html, a script for turning ANSI terminal output into reasonable HTML

    Currently at the stage of _DO NOT USE THIS_, because this does not cover the
    wide range of ANSI control codes that it needs to to avoid producing junk in
    the output. From the handful of `script` files I have here, this is working for
    me, but going to seek out more files to test with, and make the output more
    robust.

    (This doesn’t do much, so licence: CC-0)

    · John Drinkwater <john@nextraweb.com>
"""


import sys,os.path,codecs, re

__version__ = "0.01"

def printusage():
  print "typescript2html %s" % __version__
  print "Usage: %s <typescript>" % os.path.basename( __file__ )
  sys.exit(-1)

escapement = '\x1b\['
escaped = '\x1b['
USERSTART = escapement + 'y'
USEREND = escapement + 'z'

if __name__ == '__main__':

    # TODO, defaults?
    scriptfile = 'typescript'
    outputfile = 'typescript.html'

    if len(sys.argv) < 2:
        printusage()

    scriptfile = sys.argv[1]
    # export
    outputfile = os.path.splitext( scriptfile )[0] + '.html'
    formatted = codecs.open( outputfile, 'w' )

    with open( scriptfile, 'r' ) as typescript:

        data = typescript.read( )
        data = data.splitlines( False )

        # Remove the standard typescript pragma lines
        if data[0].startswith('Script'):
            data = data[1:]
        if data[-1].startswith('Script'):
            data = data[:-1]

        for index, line in enumerate( data ):

            line = re.sub( r'\r', '', line )

            # make our <pre> output tight
            line = line.rstrip( )

            line = re.sub( USERSTART, '<kbd>', line )
            line = re.sub( USEREND, '</kbd>', line )

            # replace codes we do not care about
            # OSC, xterm
            line = re.sub( '\x1b][0-9];[^\x07]*\x07', '', line )

            # break 2+3 colour modes into separate ones
            line = re.sub( escapement + '([0-9]*);([0-9]*)m', escaped + '\\1m' + escaped + '\\2m', line )
            line = re.sub( escapement + '([0-9]*);([0-9]*);([0-9]*)m', escaped + '\\1m' + escaped + '\\2m'+ escaped + '\\3m', line )
            # turn 01m reset into a 1m one
            line = re.sub( escapement + '0([0-9])m', escaped + '\\1m', line )

            # we kinda need smarter state management than re.sub, so lets tidy in this block, do that further on:
            # reset (implicit, and explicit)
            #line = re.sub( escapement + 'm', '</span>', line )
            #line = re.sub( escapement + '0m', '</span>', line )

            data[ index ] = line

        data = '\n'.join( data )
        output = ""
        characters = len( data )
        skip = 0
        state = []
        stateWritten = True

        def openState( state, output ):
            if state:
                trimmed = state[:]
                if 'bold' in trimmed:
                    trimmed.remove( 'bold' )
                if 'underline' in trimmed:
                    trimmed.remove( 'underline' )
                if trimmed:
                    output += '<span class="' + ' '.join( trimmed ) + '">'
                if 'underline' in state:
                    output += '<u>'
                if 'bold' in state:
                    output += '<b>'
            return ( state, output )

        def closeState( state, output ):
            if state:
                trimmed = state[:]
                if 'bold' in trimmed:
                    trimmed.remove( 'bold' )
                    output += '</b>'
                if 'underline' in trimmed:
                    trimmed.remove( 'underline' )
                    output += '</u>'
                if trimmed:
                    output += '</span>'
                # TODO
                state = []
            return ( state, output )

        for index in xrange( 0, characters ):

            if skip > 0:
                skip -= 1
                continue

            if '\x1b' == data[ index ] and '[' == data[ index + 1 ]:

                if 'm' == data[ index + 2 ]:
                    ( state, output ) = closeState( state, output )
                    skip = 2
                    continue
                elif 'm' == data[ index + 3 ]:
                    if '0' == data[ index + 2 ]:
                        ( state, output ) = closeState( state, output )
                        skip = 3
                        continue
                    elif '1' == data[ index + 2 ]:
                        state += ['bold']
                        stateWritten = False
                        skip = 3
                        continue
                    elif '4' == data[ index + 2 ]:
                        state += ['underline']
                        stateWritten = False
                        skip = 3
                        continue
                elif 'm' == data[ index + 4 ]:
                    number = int( data[ index + 2 ] + '' + data[ index + 3 ] )
                    if number in range( 30, 37 ):
                        state += ['f' + str( number )]
                    elif number in range( 40,47 ):
                        state += ['b' + str( number )]
                    elif number in range( 20,27 ):
                        # for the 20s, we need to clone state, close, and return state to -= flag
                        pass
                    else:
                        # lots of state we do not track yet
                        pass
                    stateWritten = False
                    skip = 4
                    continue
                elif '?' == data[ index + 2 ]:
                    # eat all data up to a character
                    idx = 3
                    forward = True
                    while forward:
                        char = data[ index + idx ]
                        if char.isdigit():
                            idx += 1
                        elif ';' == char:
                            # compound statement, still ignore
                            idx += 1
                        else:
                            forward = False
                            skip = idx
                else:
                    output += "\x1b["
                    skip = 1

            elif '\n' == data[ index ]:
                ( state, output ) = closeState( state, output )
                output += '\n'
            else:
                if not stateWritten:
                    # we want to break output <u> & <b>?
                    ( state, output ) = openState( state, output )
                    # output += '<span class="' + ' '.join( state ) + '">'
                    stateWritten = True
                output += data[ index ]

        # TODO verbose toggle required
        # print repr( output ).replace( '\\n', '\n' )

        output = '<pre class="terminal">' + output + '</pre>\n'

    formatted.write( output )
