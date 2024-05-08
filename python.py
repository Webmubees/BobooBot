import discord
from discord.ext import commands
import decouple
import mysql.connector
import pymysql

# Load environment variables
db_host = decouple.config("DB_HOST")
db_user = decouple.config("DB_USER")
db_password = decouple.config("DB_PASSWORD")
db_name = decouple.config("DB_NAME")

# Connect to the database
db_connection = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
db_cursor = db_connection.cursor()

# Function to update user role in the database
def update_user_role(discord_id, role):
    try:
        query = "INSERT INTO user_role (discord_id, role) VALUES (%s, %s)"
        values = (discord_id, role)
        db_cursor.execute(query, values)
        db_connection.commit()
        print(f"User {discord_id} assigned role {role} in the database.")
    except mysql.connector.Error as error:
        print("Failed to update user role in the database:", error)

# Function to create welcome Embeds
def create_welcome_embed(member):
    # Create an embed for the welcome channel
    embed_welcome_channel = discord.Embed(
        title="Welcome to the server",
        description="I am Boboo, the personal assistant of BobooTester who will help you.\n\nIf you have any questions or need assistance, our moderators and members are here to help.\n\nEnjoy your time here and have fun!",
        color=discord.Color.red()
    )
    embed_welcome_channel.set_image(url="https://bs-uploads.toptal.io/blackfish-uploads/components/blog_post_page/4088234/cover_image/retina_1708x683/cover-chatbot-ux-design-2f98727c40ba679ed014d2162fc0bffe.png")

    # Create an embed for the new member
    embed_new_member = discord.Embed(
        title="Welcome to the server",
        description=f"Hello! {member.name}\nI am Boboo, the personal assistant of BobooTester who will help you.\n\nIf you have any questions or need assistance, our moderators and members are here to help.\n\nEnjoy your time here and have fun!",
        color=discord.Color.blue()
    )
    embed_new_member.set_image(url="https://media.istockphoto.com/id/1060696342/vector/robot-icon-chat-bot-sign-for-support-service-concept-chatbot-character-flat-style.jpg?s=612x612&w=0&k=20&c=t9PsSDLowOAhfL1v683JMtWRDdF8w5CFsICqQvEvfzY=")

    return embed_welcome_channel, embed_new_member

# Bot initialization
mubot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# Event: Bot is ready
@mubot.event
async def on_ready():
    print("Bot is running")

# Command: Create role selection
class TestRoleSelect(discord.ui.View):
    def _init_(self, ctx):
        super()._init_()
        roles = [
            discord.SelectOption(label="QA_TESTER", value="QA_TESTER"),
            discord.SelectOption(label="BACK-END-DEVELOPER", value="BACK-END-DEVELOPER"),
            discord.SelectOption(label="FRONT-END-DEVELOPER", value="FRONT-END-DEVELOPER"),
            discord.SelectOption(label="UI-DEVELOPER", value="UI-DEVELOPER")
        ]
        self.add_item(discord.ui.Select(options=roles, placeholder="Select a role", custom_id="role_select"))
        self.ctx = ctx

# Command: Trigger role selection
@mubot.command(name="select-role")
async def create_role_select(ctx):
    view = TestRoleSelect(ctx)
    await ctx.send("Choose a role:", view=view)

# Event: Interaction handling
@mubot.event
async def on_interaction(interaction):
    if isinstance(interaction, discord.Interaction) and interaction.type == discord.InteractionType.component:
        if interaction.data["custom_id"] == "role_select":
            selected_role_name = interaction.data.get("values", ["None"])[0]
            guild = mubot.get_guild(interaction.guild_id)
            selected_role = discord.utils.get(guild.roles, name=selected_role_name)
            if selected_role:
                member = guild.get_member(interaction.user.id)
                if member:
                    await member.add_roles(selected_role)
                    try:
                        await interaction.response.send_message(f"Role '{selected_role.name}' has been assigned to you.", ephemeral=True)
                    except discord.errors.HTTPException as e:
                        if e.status == 40060:
                            pass  # Interaction already resolved
                        else:
                            print(f"Error sending message: {e}")
                    # Update user role in the database
                    update_user_role(interaction.user.id, selected_role.name)
                else:
                    await interaction.response.send_message("Error: Member not found", ephemeral=True)
            else:
                await interaction.response.send_message("Error: Role not found", ephemeral=True)
    else:
        print("Ignoring non-component interaction.")

# Event: Member joins
@mubot.event
async def on_member_join(member):   
    welcome_channel = mubot.get_channel(1237075921782181918)
    embed_welcome_channel, embed_new_member = create_welcome_embed(member)
    
    welcome_message = f"Hello! {member.name}\n"
    await welcome_channel.send(welcome_message, embed=embed_welcome_channel)
    
    # Send the welcome message with the embed to the new member
    await member.send(welcome_message, embed=embed_new_member)

# Function: Fetch data from database
def fetch_data(query):
    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)
    cursor = connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()

# Event: Message received
@mubot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Establish database connection
    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)
    cursor = connection.cursor()

    # Extract words from the message
    words = message.content.split()
    
    # Store each word along with the user's ID in the database
    for word in words:
        cursor.execute("INSERT INTO user_words (discord_id, word) VALUES (%s, %s)", (message.author.id, word))
        connection.commit()

    cursor.close()
    connection.close()

    await mubot.process_commands(message)

# Command: Check word status
@mubot.command()
async def word_status(ctx):
    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)
    cursor = connection.cursor()
    cursor.execute("SELECT word, COUNT(*) AS count FROM user_words GROUP BY word ORDER BY count DESC LIMIT 10")
    result = cursor.fetchall()

    word_status_embed = discord.Embed(
        title="Most Used Words",
        color=discord.Color.green()
    )

    for row in result:
        word_status_embed.add_field(name=row[0], value=f"Count: {row[1]}", inline=False)

    await ctx.send(embed=word_status_embed)

    cursor.close()
    connection.close()

# Command: Check user's word status
@mubot.command()
async def user_status(ctx, user: discord.Member):
    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)
    cursor = connection.cursor()
    cursor.execute("SELECT word, COUNT(*) AS count FROM user_words WHERE discord_id = %s GROUP BY word ORDER BY count DESC LIMIT 10", (user.id,))
    result = cursor.fetchall()

    user_status_embed = discord.Embed(
        title=f"Most Used Words by {user.display_name}",
        color=discord.Color.blue()
    )

    for row in result:
        user_status_embed.add_field(name=row[0], value=f"Count: {row[1]}", inline=False)

    await ctx.send(embed=user_status_embed)

    cursor.close()
    connection.close()


@mubot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, that command is not recognized.")

# Run the bot
mubot.run(decouple.config("TOKEN"))
