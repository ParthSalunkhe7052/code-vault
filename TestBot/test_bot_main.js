/**
 * Discord Moderation Bot - Node.js Version
 * A realistic bot that customers might want to license and protect
 * Mirrors the functionality of test_bot_main.py
 */

const { Client, GatewayIntentBits, EmbedBuilder, PermissionsBitField } = require('discord.js');

// Bot configuration
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
    ]
});

// In-memory storage (would be database in production)
const warningsDb = new Map();
const mutedUsers = new Map();
const autoResponses = new Map();

// Spam tracking
const spamTracker = new Map();
const bannedWords = ['badword1', 'badword2']; // Example

// Event: Bot ready
client.on('ready', () => {
    console.log(`✅ Bot logged in as ${client.user.tag}`);
    console.log(`Connected to ${client.guilds.cache.size} servers`);
    
    client.user.setActivity('the server', { type: 3 }); // WATCHING
});

// Event: New member joins
client.on('guildMemberAdd', async (member) => {
    const welcomeChannel = member.guild.channels.cache.find(ch => ch.name === 'welcome');
    
    if (welcomeChannel) {
        const embed = new EmbedBuilder()
            .setTitle(`Welcome to ${member.guild.name}! 👋`)
            .setDescription(`Hey ${member}, welcome to our server!\nMake sure to read the rules.`)
            .setColor(0x00FF00)
            .setThumbnail(member.user.displayAvatarURL());
        
        await welcomeChannel.send({ embeds: [embed] });
    }
});

// Event: Message received
client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    
    // Spam detection
    const userId = message.author.id;
    const now = Date.now();
    
    if (!spamTracker.has(userId)) {
        spamTracker.set(userId, []);
    }
    
    const userMessages = spamTracker.get(userId);
    // Remove messages older than 5 seconds
    const recentMessages = userMessages.filter(time => (now - time) < 5000);
    recentMessages.push(now);
    spamTracker.set(userId, recentMessages);
    
    if (recentMessages.length > 5) {
        await message.delete();
        const warningMsg = await message.channel.send({
            content: `⚠️ ${message.author}, please slow down! (Anti-spam)`
        });
        setTimeout(() => warningMsg.delete(), 3000);
        return;
    }
    
    // Banned words detection
    const contentLower = message.content.toLowerCase();
    if (bannedWords.some(word => contentLower.includes(word))) {
        await message.delete();
        const warningMsg = await message.channel.send({
            content: `⚠️ ${message.author}, your message contained inappropriate content!`
        });
        setTimeout(() => warningMsg.delete(), 5000);
        return;
    }
    
    // Command handling
    if (!message.content.startsWith('!')) return;
    
    const args = message.content.slice(1).trim().split(/ +/);
    const command = args.shift().toLowerCase();
    
    // Warn command
    if (command === 'warn') {
        if (!message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)) {
            return message.reply('❌ You do not have permission to use this command!');
        }
        
        const member = message.mentions.members.first();
        if (!member) return message.reply('❌ Please mention a user to warn!');
        
        const reason = args.slice(1).join(' ') || 'No reason provided';
        
        if (!warningsDb.has(member.id)) {
            warningsDb.set(member.id, []);
        }
        
        const warning = {
            timestamp: new Date().toISOString(),
            moderator: message.author.id,
            reason: reason
        };
        
        warningsDb.get(member.id).push(warning);
        
        const embed = new EmbedBuilder()
            .setTitle('⚠️ User Warned')
            .setColor(0xFFA500)
            .setTimestamp()
            .addFields(
                { name: 'User', value: member.toString(), inline: true },
                { name: 'Moderator', value: message.author.toString(), inline: true },
                { name: 'Reason', value: reason, inline: false },
                { name: 'Total Warnings', value: warningsDb.get(member.id).length.toString(), inline: false }
            );
        
        await message.channel.send({ embeds: [embed] });
        
        // Auto-mute after 3 warnings
        if (warningsDb.get(member.id).length >= 3) {
            await autoMute(message, member, 3600);
        }
    }
    
    // Check warnings command
    if (command === 'warnings') {
        const member = message.mentions.members.first() || message.member;
        
        if (!warningsDb.has(member.id) || warningsDb.get(member.id).length === 0) {
            return message.channel.send(`✅ ${member.displayName} has no warnings!`);
        }
        
        const embed = new EmbedBuilder()
            .setTitle(`⚠️ Warnings for ${member.displayName}`)
            .setColor(0xFF0000)
            .setTimestamp();
        
        warningsDb.get(member.id).forEach((warning, index) => {
            embed.addFields({
                name: `Warning #${index + 1}`,
                value: `**Reason:** ${warning.reason}\n**Date:** ${warning.timestamp.substring(0, 10)}`,
                inline: false
            });
        });
        
        await message.channel.send({ embeds: [embed] });
    }
    
    // Clear warnings command
    if (command === 'clearwarnings') {
        if (!message.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return message.reply('❌ You do not have permission to use this command!');
        }
        
        const member = message.mentions.members.first();
        if (!member) return message.reply('❌ Please mention a user!');
        
        if (warningsDb.has(member.id)) {
            warningsDb.set(member.id, []);
            await message.channel.send(`✅ Cleared all warnings for ${member}`);
        } else {
            await message.channel.send(`ℹ️ ${member} has no warnings to clear`);
        }
    }
    
    // Server info command
    if (command === 'serverinfo') {
        const guild = message.guild;
        
        const embed = new EmbedBuilder()
            .setTitle(`📊 ${guild.name} Server Info`)
            .setColor(0x0000FF)
            .setTimestamp()
            .setThumbnail(guild.iconURL());
        
        embed.addFields(
            { name: 'Owner', value: `<@${guild.ownerId}>`, inline: true },
            { name: 'Members', value: guild.memberCount.toString(), inline: true },
            { name: 'Channels', value: guild.channels.cache.size.toString(), inline: true },
            { name: 'Roles', value: guild.roles.cache.size.toString(), inline: true },
            { name: 'Created On', value: guild.createdAt.toISOString().substring(0, 10), inline: true },
            { name: 'Boost Level', value: `Level ${guild.premiumTier}`, inline: true }
        );
        
        await message.channel.send({ embeds: [embed] });
    }
    
    // Poll command
    if (command === 'poll') {
        const question = args[0];
        const options = args.slice(1);
        
        if (options.length > 10) {
            return message.reply('❌ Maximum 10 options allowed!');
        }
        
        if (options.length < 2) {
            return message.reply('❌ Please provide at least 2 options!');
        }
        
        const reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];
        
        let description = '';
        options.forEach((option, index) => {
            description += `\n${reactions[index]} ${option}`;
        });
        
        const embed = new EmbedBuilder()
            .setTitle(`📊 ${question}`)
            .setColor(0x00FF00)
            .setDescription(description)
            .setFooter({ text: `Poll by ${message.author.displayName}` });
        
        const pollMessage = await message.channel.send({ embeds: [embed] });
        
        for (let i = 0; i < options.length; i++) {
            await pollMessage.react(reactions[i]);
        }
    }
});

// Auto-mute function
async function autoMute(message, member, duration) {
    let muteRole = message.guild.roles.cache.find(role => role.name === 'Muted');
    
    if (!muteRole) {
        muteRole = await message.guild.roles.create({
            name: 'Muted',
            reason: 'Auto-mute system'
        });
        
        message.guild.channels.cache.forEach(async (channel) => {
            await channel.permissionOverwrites.edit(muteRole, {
                SendMessages: false,
                Speak: false
            });
        });
    }
    
    await member.roles.add(muteRole);
    mutedUsers.set(member.id, Date.now() + (duration * 1000));
    
    await message.channel.send({
        content: `🔇 ${member} has been auto-muted for 1 hour due to excessive warnings!`
    });
    
    // Schedule unmute
    setTimeout(async () => {
        if (mutedUsers.has(member.id)) {
            await member.roles.remove(muteRole);
            mutedUsers.delete(member.id);
        }
    }, duration * 1000);
}

// Error handling
client.on('error', (error) => {
    console.error('Discord client error:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('Unhandled promise rejection:', error);
});

// Main entry point
const TOKEN = process.env.DISCORD_BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
client.login(TOKEN);
