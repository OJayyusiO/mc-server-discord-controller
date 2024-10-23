import discord
from discord.ext import commands, tasks
import time
import asyncio
import subprocess
from mcstatus import JavaServer
import os
import signal

bot = commands.Bot(command_prefix=".", intents = discord.Intents.all())

with open("serverbat.txt") as file:
    server_file = file.read()

server = JavaServer.lookup('localhost', 25565)
server_process = None
server_active = False
last_active_time = 0
inactive_timer = 30 * 60  # 30 minutes in seconds

@bot.event
async def on_ready():
    print("Bot ready!")
    try:
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} commands.")
    
    except Exception as e:
        print("An error with syncing application commands has occured: ", e)


# Minecraft Server Commands


@tasks.loop(minutes=1)  # Check every minute
async def auto_stop():
    global last_active_time, server_active
    print("Checking server status...")
    if server_active:
        try:
            status = server.status()
            print(f"Current players online: {status.players.online}")
            if status.players.online > 0:
                print("Players are online, updating last active time.")
                last_active_time = time.time()  # Update last active time if players are online
            else:
                inactive_time = time.time() - last_active_time
                print(f"Inactive time: {inactive_time} seconds")

                if inactive_time >= inactive_timer:
                    print("Inactive time exceeded, stopping server.")
                    
                    if not server_active:
                        print("The Minecraft server is not running!")
                        return

                    try:
                    # Send the /stop command to the server
                        server_process.stdin.write(b'stop\n')  # Send the stop command
                        server_process.stdin.flush()  # Ensure the command is sent immediately

                        print("Minecraft server is shutting down for inactivity...")
        
                    # Wait for the server to close gracefully
                        server_process.wait()  # This will block until the process exits
                        server_active = False
                    except Exception as e:
                        print(f"Failed to stop the server: {e}")
        except Exception as e:
            print(f"Error checking server status: {e}")
    else:
        auto_stop.stop()
        print("Auto stop loop stopped since the server is not active.")



@bot.tree.command(name="start", description="Starts the Minecraft server")
async def start_minecraft_server(interaction: discord.Interaction):
    global server_process, server_active, last_active_time
    if server_active:
        await interaction.response.send_message("The Minecraft server is already running!")
        return

    # Defer the response to give yourself more time
    await interaction.response.defer(thinking=True)

    try:
        # Start the Minecraft server using subprocess
        server_process = subprocess.Popen(
            [server_file], 
            shell=True,
            stdin=subprocess.PIPE
        )
        server_active = True
        last_active_time = time.time()
        auto_stop.start()
        
        await interaction.followup.send("Minecraft server starting, it will take about 3-4 minutes to start.")
    except Exception as e:
        await interaction.followup.send(f"Failed to start the server: {e}")


@bot.tree.command(name="stop", description="Stops the Minecraft server safely")
async def stop_minecraft_server(interaction: discord.Interaction):
    global server_process, server_active

    if not server_active:
        await interaction.response.send_message("The Minecraft server is not running!")
        return

    try:
        # Send the /stop command to the server
        server_process.stdin.write(b'stop\n')  # Send the stop command
        server_process.stdin.flush()  # Ensure the command is sent immediately

        await interaction.response.send_message("Minecraft server is shutting down...")
        
        # Wait for the server to close gracefully
        server_process.wait()  # This will block until the process exits
        server_active = False
    
    except Exception as e:
        await interaction.response.send_message(f"Failed to stop the server: {e}")


@bot.tree.command(name="status", description="Checks server activity")
async def server_status(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)  # Acknowledge the interaction immediately
    
    try:
        global server
        status = server.status()
        response = f"Server is online with {status.players.online} player(s) playing and {round(inactive_timer-(time.time() - last_active_time))} seconds left (aprox.)"
    except Exception:
        response = "The server is offline or not reachable."
    
    # Now send the follow-up response
    await interaction.followup.send(response)


with open("token.txt") as file:
    token = file.read()
# Run the bot with your token
bot.run(token)

