import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import asyncio

TOKEN = os.getenv("TOKEN")

STAFF_ROLE_ID = None
LOG_CHANNEL_ID = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

tickets_abertos = {}
cooldown_ticket = {}

# ==========================================
# AUTO FECHAR TICKET
# ==========================================

async def auto_fechar_ticket(canal, user_id):

    await asyncio.sleep(14400)  # 4 HORAS

    try:

        log_channel = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None

        embed = discord.Embed(
            title="⏰ Ticket fechado automaticamente",
            description=canal.name,
            color=0xff0000
        )

        if log_channel:
            await log_channel.send(embed=embed)

        tickets_abertos.pop(user_id, None)

        await canal.delete()

    except:
        pass

# ==========================================
# EMBED BUILDER
# ==========================================

class EmbedModal(discord.ui.Modal, title="Criar Embed"):

    titulo = discord.ui.TextInput(label="Título")

    descricao = discord.ui.TextInput(
        label="Mensagem",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    cor = discord.ui.TextInput(
        label="Cor HEX",
        required=False
    )

    imagem = discord.ui.TextInput(
        label="Imagem URL",
        required=False
    )

    rodape = discord.ui.TextInput(
        label="Rodapé",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            cor = int(self.cor.value.replace("#", ""), 16)

        except:
            cor = 0x2b2d31

        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=cor
        )

        if self.imagem.value:
            embed.set_thumbnail(url=self.imagem.value)

        if self.rodape.value:
            embed.set_footer(
                text=f"{self.rodape.value} | {interaction.user}"
            )

        await interaction.response.send_message(
            embed=embed
        )

@tree.command(name="embed")
async def embed_cmd(interaction: discord.Interaction):

    await interaction.response.send_modal(
        EmbedModal()
    )

# ==========================================
# CONTROLES TICKET
# ==========================================

class TicketControls(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.red,
        custom_id="fechar_ticket"
    )
    async def fechar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if STAFF_ROLE_ID:

            if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:

                return await interaction.response.send_message(
                    "Apenas staff pode fechar tickets.",
                    ephemeral=True
                )

        log_channel = bot.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None

        embed = discord.Embed(
            title="❌ Ticket fechado",
            description=interaction.channel.name,
            color=0xff0000
        )

        if log_channel:
            await log_channel.send(embed=embed)

        try:

            user_id = int(interaction.channel.name.split("-")[-1])

            tickets_abertos.pop(user_id, None)

        except:
            pass

        await interaction.channel.delete()

# ==========================================
# MODAL TICKET
# ==========================================

class TicketModal(discord.ui.Modal, title="Solicitar Tag"):

    def __init__(self, plataforma):
        super().__init__()

        self.plataforma = plataforma

    nome = discord.ui.TextInput(
        label="Qual seu nick no game?"
    )

    tempo = discord.ui.TextInput(
        label="Quanto tempo faz lives/vídeos?"
    )

    frequencia = discord.ui.TextInput(
        label="Qual é sua frequência?",
        style=discord.TextStyle.paragraph
    )

    link = discord.ui.TextInput(
        label="Link do canal/perfil"
    )

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📩 Nova Solicitação",
            color=0x00ff88
        )

        embed.add_field(
            name="Nome",
            value=self.nome.value,
            inline=False
        )

        embed.add_field(
            name="Tempo",
            value=self.tempo.value,
            inline=False
        )

        embed.add_field(
            name="Frequência",
            value=self.frequencia.value,
            inline=False
        )

        embed.add_field(
            name="Plataforma",
            value=self.plataforma,
            inline=False
        )

        embed.add_field(
            name="Link",
            value=self.link.value,
            inline=False
        )

        await interaction.response.send_message(
            "✅ Solicitação enviada!",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed)

# ==========================================
# SELECT PLATAFORMAS
# ==========================================

class PlatformSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="YouTube",
                emoji="📺"
            ),

            discord.SelectOption(
                label="TikTok",
                emoji="🎵"
            ),

            discord.SelectOption(
                label="Twitch",
                emoji="🟣"
            ),

            discord.SelectOption(
                label="Kick",
                emoji="🟢"
            ),
        ]

        super().__init__(
            placeholder="Escolha a plataforma",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="platform_select"
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            TicketModal(self.values[0])
        )

# ==========================================
# VIEW INICIAL
# ==========================================

class StartView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(PlatformSelect())

# ==========================================
# CRIAR TICKET
# ==========================================

async def criar_ticket(interaction: discord.Interaction):

    user_id = interaction.user.id

    agora = datetime.datetime.now()

    # VERIFICA SE JÁ TEM TICKET

    if user_id in tickets_abertos:

        return await interaction.response.send_message(
            "❌ Você já possui um ticket aberto.",
            ephemeral=True
        )

    # COOLDOWN

    if user_id in cooldown_ticket:

        if (agora - cooldown_ticket[user_id]).days < 7:

            return await interaction.response.send_message(
                "⏰ Você precisa esperar 7 dias.",
                ephemeral=True
            )

    await interaction.response.defer(ephemeral=True)

    tickets_abertos[user_id] = True

    guild = interaction.guild

    nome_usuario = interaction.user.name.lower().replace(" ", "-")

    staff_role = guild.get_role(STAFF_ROLE_ID) if STAFF_ROLE_ID else None

    overwrites = {

        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )
    }

    if staff_role:

        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )

    canal = await guild.create_text_channel(

        name=f"solicitartag-{nome_usuario}-{user_id}",

        category=interaction.channel.category,

        overwrites=overwrites
    )

    await canal.send(
        "⏰ Este ticket será fechado automaticamente em 4 horas.",
        view=TicketControls()
    )

    await canal.send(
        "Selecione sua plataforma abaixo:",
        view=StartView()
    )

    cooldown_ticket[user_id] = agora

    bot.loop.create_task(
        auto_fechar_ticket(canal, user_id)
    )

    await interaction.followup.send(
        f"✅ Ticket criado: {canal.mention}",
        ephemeral=True
    )

# ==========================================
# CONFIRMAR TICKET
# ==========================================

class ConfirmarTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Abrir Ticket",
        style=discord.ButtonStyle.green,
        custom_id="abrir_ticket"
    )
    async def confirmar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await criar_ticket(interaction)

# ==========================================
# PAINEL
# ==========================================

class TicketPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(

        placeholder="Escolha o ticket",

        custom_id="ticket_select",

        options=[
            discord.SelectOption(
                label="Solicitar Tag",
                emoji="🎫"
            )
        ]
    )
    async def select_callback(
        self,
        interaction: discord.Interaction,
        select
    ):

        await interaction.response.send_message(

            "Clique no botão abaixo para abrir seu ticket.",

            view=ConfirmarTicketView(),

            ephemeral=True
        )

# ==========================================
# MODAL CONFIGURAR PAINEL
# ==========================================

class PainelModal(discord.ui.Modal, title="Configurar Painel"):

    titulo = discord.ui.TextInput(label="Título")

    descricao = discord.ui.TextInput(
        label="Mensagem",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    imagem = discord.ui.TextInput(
        label="Imagem URL",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(

            title=self.titulo.value,

            description=self.descricao.value,

            color=0x3498db
        )

        if self.imagem.value:

            embed.set_image(url=self.imagem.value)

        await interaction.response.send_message(

            embed=embed,

            view=TicketPanel()
        )

# ==========================================
# COMANDO CONFIGURAR PAINEL
# ==========================================

@tree.command(name="configurar_painel")
async def painel(interaction: discord.Interaction):

    await interaction.response.send_modal(
        PainelModal()
    )

# ==========================================
# ADMIN
# ==========================================

@tree.command(name="setar_cargo")
async def setar_cargo(
    interaction: discord.Interaction,
    cargo: discord.Role
):

    global STAFF_ROLE_ID

    STAFF_ROLE_ID = cargo.id

    await interaction.response.send_message(
        f"✅ Cargo staff definido: {cargo.mention}",
        ephemeral=True
    )

@tree.command(name="setar_logs")
async def setar_logs(
    interaction: discord.Interaction,
    canal: discord.TextChannel
):

    global LOG_CHANNEL_ID

    LOG_CHANNEL_ID = canal.id

    await interaction.response.send_message(
        f"✅ Canal de logs definido: {canal.mention}",
        ephemeral=True
    )

# ==========================================
# READY
# ==========================================

@bot.event
async def on_ready():

    # REGISTRAR VIEWS PERSISTENTES

    bot.add_view(TicketPanel())
    bot.add_view(StartView())
    bot.add_view(ConfirmarTicketView())
    bot.add_view(TicketControls())

    await tree.sync()

    print(f"✅ Online como {bot.user}")

# ==========================================
# INICIAR BOT
# ==========================================

bot.run(TOKEN)
