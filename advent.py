import re, os, hashlib
import adventure, adventure.game
from curses.ascii import isalnum
from halibot import HalModule, HalConfigurer

class Adventure(HalModule):

    class Configurer(HalConfigurer):
        def configure(self):
            self.optionString('save-directory', prompt='Directory to place save files in', default='advent-saves')

    class Context():
        def __init__(self):
            self.running = False
            self.game = adventure.game.Game()
            adventure.load_advent_dat(self.game)

    topics = {
        'adventure': '''Play colossal cave adventure!

Usage:
  !adventure begin
  !adventure resume [save name]'''
    }

    def init(self):
        self.context = {}

    def init_context(self, ctx):
        self.context[ctx] = Adventure.Context()
        self.make_suspend_hook(ctx)

    # Hook save function to add prefix and chop out dangerous paths
    # Also make the save function context-specific
    def make_suspend_hook(self, ctx):
        suspend = self.context[ctx].game.t_suspend

        def hook_suspend(v, n):
            path = self.savepath(n, ctx)
            self.log.info('Suspending to file "{}".'.format(path))

            self.context[ctx].game.t_suspend = None          # Can't pickle a function
            rv = suspend(v, path)                            # Call the actual suspend function
            self.context[ctx].game.t_suspend = hook_suspend  # Put the hook back

        self.context[ctx].game.t_suspend = hook_suspend

    def savepath(self, name, ctx):
        # Chop out all non-alphabetic/digits
        # Otherwise this might be dangerous
        name = ''.join([c for c in name if isalnum(c)]).upper()

        # Hash the context
        ctxhash = hashlib.md5(ctx.encode()).hexdigest()

        # Get the prefix and make sure it exists
        prefix = self.config.get('save-prefix', 'advent-saves')
        if not os.path.exists(prefix):
            os.mkdir(prefix)

        return os.path.join(prefix, ctxhash + '.' + name)

    def resume(self, name, ctx):
        path = self.savepath(name, ctx)
        if os.path.exists(path):
            self.context[ctx].game = adventure.game.Game.resume(path)
            self.context[ctx].running = True
            return 'GAME RESUMED'
        else:
            return 'I DON\'T HAVE A SAVE FILE BY THAT NAME'

    def receive(self, msg):
        cmds = re.findall('[^ ]+', msg.body)

        ctx = msg.origin
        if not ctx in self.context:
            self.init_context(ctx)

        # Need .running because this is initially False
        if self.context[ctx].running and self.context[ctx].game.is_finished:
            self.context[ctx].running = False

        if not self.context[ctx].running:
            if cmds[0] == '!adventure':
                if len(cmds) >= 2:
                    if cmds[1] == 'begin':
                        self.context[ctx].game.start()
                        self.context[ctx].running = True
                        resp = self.context[ctx].game.output
                    elif cmds[1] == 'resume':
                        if len(cmds) == 2:
                            resp = 'RESUME WHAT?'
                        else:
                            resp = self.resume(cmds[2], ctx)
                    else:
                        resp = 'I DON\'T UNDERSTAND'
                else:
                    resp = 'ADVENTURE WHAT?'
                self.reply(msg, body=resp)
        else:
            self.context[ctx].game.do_command(cmds)
            self.reply(msg, body=self.context[ctx].game.output)

