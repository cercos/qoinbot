import discord
import traceback
import psutil
import os
import chalk
from datetime import datetime
from discord.ext import commands
from discord.ext.commands import errors
from prodict import Prodict

from models import Guild
from utils import default


async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        await ctx.send_help(str(ctx.invoked_subcommand))
    else:
        await ctx.send_help(str(ctx.command))


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = default.get("config.json")
        self.process = psutil.Process(os.getpid())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):
        if isinstance(err, errors.MissingRequiredArgument) or isinstance(err, errors.BadArgument):
            await send_cmd_help(ctx)

        elif isinstance(err, errors.CommandInvokeError):
            err = err.original

            _traceback = traceback.format_tb(err.__traceback__)
            _traceback = ''.join(_traceback)
            error = ('```py\n{2}{0}: {3}\n```').format(type(err).__name__, ctx.message.content, _traceback, err)

            await ctx.send(f'```diff\n-There was an error processing the command: {ctx.command}```{error}')
        elif isinstance(err, errors.CheckFailure):
            pass

        elif isinstance(err, errors.CommandOnCooldown):
            await ctx.send(f"```fix\nThis command is on cooldown... try again in {err.retry_after:.2f} seconds.```")

        elif isinstance(err, errors.CommandNotFound):
            pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        guild_template = {
            'guild_id': str(guild.id),
            'name': guild.name,
            'prefix': self.config.prefix
        }
        guild_id = Guild.insert_one(guild_template).inserted_id
        print(chalk.cyan(f"Joined Guild > ") + chalk.yellow(f'{guild.name}'))
        if not self.config.join_message:
            return

        try:
            to_send = sorted([chan for chan in guild.channels if
                              chan.permissions_for(guild.me).send_messages and isinstance(chan, discord.TextChannel)],
                             key=lambda x: x.position)[0]
        except IndexError:
            pass
        else:
            await to_send.send(self.config.join_message)
            botguild = next((item for item in self.bot.guilds if item.id == 615228970568515626), None)
            log = botguild.get_channel(625767405641007106)
            await log.send(f"```css\nJoined Guild > {guild.name}```")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        botguild = next((item for item in self.bot.guilds if item.id == 615228970568515626), None)
        log = botguild.get_channel(625767405641007106)
        try:
            print(chalk.bold(chalk.cyan(f'{ctx.guild.name}')) + chalk.yellow(' > ') + chalk.bold(
                chalk.green(f'{ctx.author}')) + chalk.yellow(': ') + f'{ctx.message.clean_content}')
            await log.send(f'```md\n[{ctx.guild.name}]({ctx.channel.name}) {ctx.author}: {ctx.message.clean_content}```')

        except AttributeError:
            print(chalk.yellow(f"Private message > {ctx.author} > {ctx.message.clean_content}"))
            await log.send(f'```md\n< Private message > {ctx.author}: {ctx.message.clean_content}```')

    @commands.Cog.listener()
    async def on_ready(self):
        botguild = next((item for item in self.bot.guilds if item.id == 615228970568515626), None)
        log = botguild.get_channel(625767405641007106)
        if not hasattr(self.bot, 'uptime'):
            self.bot.uptime = datetime.utcnow()

        print(chalk.bold(chalk.cyan('Ready: ')) + chalk.green(f'{self.bot.user}') + chalk.yellow(' | ') + chalk.bold(
            chalk.cyan('Servers: ')) + chalk.green(
            f'{len(self.bot.guilds)}'))
        await self.bot.change_presence(activity=discord.Game(type=0, name=self.config.playing),
                                       status=discord.Status.online)

        await log.send(f'```css\nReady! Guilds: {len(self.bot.guilds)}```')


def setup(bot):
    bot.add_cog(Events(bot))
