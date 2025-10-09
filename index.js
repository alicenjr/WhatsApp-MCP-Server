// index.js - super simple WhatsApp MCP
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// WhatsApp client with session stored locally
const client = new Client({
    authStrategy: new LocalAuth()
});

let isClientReady = false;

// Show QR code to scan in terminal
client.on('qr', qr => {
    qrcode.generate(qr, { small: true });
    console.log('Scan this QR code with your WhatsApp app!');
});

// WhatsApp ready
client.on('ready', () => {
    isClientReady = true;
    console.log('WhatsApp is ready!');
});

client.on('auth_failure', (message) => {
    console.error('Auth failure:', message);
});

client.on('disconnected', (reason) => {
    isClientReady = false;
    console.warn('WhatsApp disconnected:', reason);
});

// Listen to incoming messages
client.on('message', msg => {
    console.log(`Message from ${msg.from}: ${msg.body}`);
});

// MCP endpoint: get last 20 messages (dummy for now)
app.get('/', (req, res) => {
    res.send('<h1>WhatsApp MCP Server</h1><p>Try <code>/mcp/get_recent_messages</code> or POST to <code>/mcp/send_message</code>.</p>');
});

app.get('/mcp/get_recent_messages', async (req, res) => {
    if (!isClientReady) {
        return res.status(503).json({ ok: false, error: 'WhatsApp client not ready. Please scan QR or wait.' });
    }

    const { to, chatId, limit } = req.query;
    const count = Math.min(parseInt(limit || '10', 10) || 10, 50);

    let targetChatId = chatId;
    if (!targetChatId && to) {
        targetChatId = normalizeWhatsAppId(String(to));
    }

    if (!targetChatId) {
        return res.status(400).json({ ok: false, error: 'Provide to or chatId' });
    }

    try {
        const chat = await client.getChatById(targetChatId);
        const messages = await chat.fetchMessages({ limit: Math.max(count, 10) });
        const textMessages = messages
            .filter(m => typeof m.body === 'string' && m.body.trim().length > 0)
            .slice(-count)
            .map(m => ({
                id: m.id?._serialized || m.id || undefined,
                from: m.from,
                to: m.to,
                author: m.author || undefined,
                body: m.body,
                timestamp: m.timestamp,
                fromMe: m.fromMe === true
            }));

        res.json({ ok: true, chatId: targetChatId, count: textMessages.length, messages: textMessages });
    } catch (err) {
        console.error('Failed to get recent messages:', err);
        res.status(500).json({ ok: false, error: err && err.message ? err.message : String(err) });
    }
});

// MCP endpoint: send message
app.post('/mcp/send_message', async (req, res) => {
    const { to, text, message } = req.body || {};
    const bodyText = text ?? message;

    if (!to || !bodyText) {
        return res.status(400).json({ ok: false, error: 'Missing required fields: to, text' });
    }

    if (!isClientReady) {
        return res.status(503).json({ ok: false, error: 'WhatsApp client not ready. Please scan QR or wait.' });
    }

    const normalizedTo = normalizeWhatsAppId(to);

    try {
        await client.sendMessage(normalizedTo, bodyText);
        res.json({ ok: true });
    } catch (err) {
        console.error('Failed to send message:', err);
        res.status(500).json({ ok: false, error: err && err.message ? err.message : String(err) });
    }
});

function normalizeWhatsAppId(recipient) {
    // Accepts formats: "1234567890" => "1234567890@c.us"; passes through if already has domain
    if (typeof recipient !== 'string') return recipient;
    if (recipient.endsWith('@c.us') || recipient.endsWith('@g.us')) return recipient;
    const digitsOnly = recipient.replace(/\D/g, '');
    if (digitsOnly.length > 0) return `${digitsOnly}@c.us`;
    return recipient;
}

// Start server
app.listen(3000, () => console.log('MCP server running on http://localhost:3000'));

// Start WhatsApp client
client.initialize();
