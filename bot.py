import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os

TOKEN = os.getenv("TOKEN")

print("DEBUG TOKEN:", TOKEN)

STAFF_ROLE_ID = None
LOG_CHANNEL_ID = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

tickets_abertos = {}
cooldown_ticket = {}

# =========================
# EMBED BUILDER
# =========================

class EmbedModal(discord.ui.Modal, title="Criar Embed"):

    titulo = discord.ui.TextInput(label="Título")
    descricao = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph)
    cor = discord.ui.TextInput(label="Cor HEX (#000000)", required=False)
    imagem = discord.ui.TextInput(label="Imagem URL", required=False)
    rodape = discord.ui.TextInput(label="Rodapé", required=False)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            cor = int(self.cor.value.replace("#", ""), 16) if self.cor.value else 0x2b2d31
        except:
            cor = 0x2b2d31

        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=cor
        )

        if self.imagem.value:
            embed.set_thumbnail(url=self.imagem.value)

        embed.set_footer(text=f"{self.rodape.value} | Enviado por {interaction.user}")

        await interaction.response.send_message(embed=embed)

@tree.command(name="embed")
async def embed_cmd(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())

# =========================
# BOTÃO FECHAR
# =========================

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red)
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not STAFF_ROLE_ID or STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Apenas staff.", ephemeral=True)

        log_channel = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None

        mensagens = []
        async for msg in interaction.channel.history(limit=200):
            mensagens.append(f"{msg.author}: {msg.content}")

        transcript = "\n".join(reversed(mensagens))

        embed = discord.Embed(
            title="Ticket fechado",
            description=interaction.channel.name,
            color=0xff0000
        )

        embed.add_field(name="Fechado por", value=interaction.user.mention)

        if log_channel:
            await log_channel.send(embed=embed)
            await log_channel.send(f"```{transcript[:1900]}```")

        user_id = int(interaction.channel.name.split("-")[-1]) if "-" in interaction.channel.name else None
        if user_id:
            tickets_abertos.pop(user_id, None)

        await interaction.channel.delete()

# =========================
# MODAL TICKET
# =========================

class TicketModal(discord.ui.Modal, title="Solicitar Tag"):

    def __init__(self, plataforma):
        super().__init__()
        self.plataforma = plataforma

    nome = discord.ui.TextInput(label="Qual seu nome?")
    tempo = discord.ui.TextInput(label="Tempo de criação")
    frequencia = discord.ui.TextInput(label="Frequência de postagens", style=discord.TextStyle.paragraph)
    link = discord.ui.TextInput(label="Link")

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(title="Nova Solicitação", color=0x00ff88)

        embed.add_field(name="Nome", value=self.nome.value, inline=False)
        embed.add_field(name="Tempo", value=self.tempo.value, inline=False)
        embed.add_field(name="Frequência", value=self.frequencia.value, inline=False)
        embed.add_field(name="Plataforma", value=self.plataforma, inline=False)
        embed.add_field(name="Link", value=self.link.value, inline=False)

        await interaction.response.send_message("Enviado!", ephemeral=True)
        await interaction.channel.send(embed=embed)

# =========================
# SELECT PLATAFORMA
# =========================

class PlatformSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="YouTube"),
            discord.SelectOption(label="TikTok"),
            discord.SelectOption(label="Twitch"),
            discord.SelectOption(label="Kick"),
        ]

        super().__init__(min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class StartView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(PlatformSelect())

# =========================
# CRIAR TICKET
# =========================

async def criar_ticket(interaction: discord.Interaction):

    user_id = interaction.user.id
    agora = datetime.datetime.now()

    if user_id in tickets_abertos:
        return await interaction.response.send_message("Você já tem ticket!", ephemeral=True)

    if user_id in cooldown_ticket:
        if (agora - cooldown_ticket[user_id]).days < 7:
            return await interaction.response.send_message("Espere 7 dias.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    tickets_abertos[user_id] = True

    nome_usuario = interaction.user.name.lower().replace(" ", "-")

    canal = await interaction.guild.create_text_channel(
        name=f"solicitartag-{nome_usuario}",
        category=interaction.channel.category
    )

    await canal.set_permissions(interaction.guild.default_role, view_channel=False)
    await canal.set_permissions(interaction.user, view_channel=True)

    staff = interaction.guild.get_role(STAFF_ROLE_ID) if STAFF_ROLE_ID else None
    if staff:
        await canal.set_permissions(staff, view_channel=True)

    await canal.send(f"{interaction.user.mention}", view=TicketControls())
    await canal.send(view=StartView())

    cooldown_ticket[user_id] = agora

    await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)

# =========================
# CONFIRMAR BOTÃO
# =========================

class ConfirmarTicketView(discord.ui.View):
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_ticket(interaction)

# =========================
# PAINEL
# =========================

class TicketPanel(discord.ui.View):
    @discord.ui.select(
        placeholder="Escolha o ticket",
        options=[discord.SelectOption(label="Solicitar Tag")]
    )
    async def select_callback(self, interaction: discord.Interaction, select):

        await interaction.response.send_message(
            "Clique abaixo para abrir o ticket",
            view=ConfirmarTicketView(),
            ephemeral=True
        )

# =========================
# MODAL PAINEL
# =========================

class PainelModal(discord.ui.Modal, title="Configurar Painel"):

    titulo = discord.ui.TextInput(label="Título")
    descricao = discord.ui.TextInput(label="Mensagem")

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=0x3498db
        )

        await interaction.response.send_message(embed=embed, view=TicketPanel())

@tree.command(name="configurar_painel")
async def painel(interaction: discord.Interaction):
    await interaction.response.send_modal(PainelModal())

# =========================
# COMANDOS ADMIN
# =========================

@tree.command(name="setar_cargo")
async def setar_cargo(interaction: discord.Interaction, cargo: discord.Role):
    global STAFF_ROLE_ID
    STAFF_ROLE_ID = cargo.id
    await interaction.response.send_message("Cargo setado!", ephemeral=True)

@tree.command(name="setar_logs")
async def setar_logs(interaction: discord.Interaction, canal: discord.TextChannel):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = canal.id
    await interaction.response.send_message("Logs setados!", ephemeral=True)

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Online como {bot.user}")

bot.run(TOKEN)
