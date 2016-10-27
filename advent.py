import re, os
import adventure, adventure.game
from curses.ascii import isalnum
from halibot import HalModule

class Adventure(HalModule):

    options = {
        'save-directory': {
            'type'    : 'string',
            'prompt'  : 'Directory to place save files in',
            'default' : 'advent-saves',
        },
    }

    def init(self):
        self.running = False
        self.game = adventure.game.Game()
        adventure.load_advent_dat(self.game)
        self.make_suspend_hook()

    # Hook save function to add prefix and chop out dangerous paths
    def make_suspend_hook(self):
        suspend = self.game.t_suspend

        def hook_suspend(v, n):
            path = self.savepath(n)
            self.log.info('Suspending to file "{}".'.format(path))

            self.game.t_suspend = None          # Can't pickle a function
            rv = suspend(v, path)               # Call the actual suspend function
            self.game.t_suspend = hook_suspend  # Put the hook back

        self.game.t_suspend = hook_suspend

    def savepath(self, name):
        # Chop out all non-alphabetic/digits
        # Otherwise this might be dangerous
        name = ''.join([c for c in name if isalnum(c)])

        # Get the prefix and make sure it exists
        prefix = self.config.get('save-prefix', 'advent-saves')
        if not os.path.exists(prefix):
            os.mkdir(prefix)

        return os.path.join(prefix, name)

    def resume(self, name):
        path = self.savepath(name)
        if os.path.exists(path):
            self.game = adventure.game.Game.resume(path)
            self.running = True
            return 'GAME RESUMED'
        else:
            return 'I DON\'T HAVE A SAVE FILE BY THAT NAME'

    def receive(self, msg):
        cmds = re.findall('[^ ]+', msg.body)

        # Need .running because this is initially False
        if self.running and self.game.is_finished:
            self.running = False 

        if not self.running:
            if cmds[0] == '!adventure':
                if len(cmds) >= 2:
                    if cmds[1] == 'begin':
                        self.game.start()
                        self.running = True
                        resp = self.game.output
                    elif cmds[1] == 'resume':
                        if len(cmds) == 2:
                            resp = 'RESUME WHAT?'
                        else:
                            resp = self.resume(cmds[2])
                    else:
                        resp = 'I DON\'T UNDERSTAND'
                else:
                    resp = 'ADVENTURE WHAT?'
                self.reply(msg, body=resp)
        else:
            self.game.do_command(cmds)
            self.reply(msg, body=self.game.output)

