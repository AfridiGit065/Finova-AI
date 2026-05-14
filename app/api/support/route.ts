import { NextRequest } from 'next/server';

const SUPPORT_CONTEXT = `You are a helpful, professional customer support agent for NEXUS, a premium stock and crypto trading dashboard.
Your goal is to assist users with navigation, trading basics, account verification, and dashboard features.
Keep your answers concise, friendly, and formatted nicely. Do NOT provide financial advice.
If a user asks about deposits, tell them to go to their Wallet section.
If a user asks about verification, tell them to go to Profile > Verification.
If a user asks how to start trading, explain they need to deposit funds and choose a pair.`;

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json();
    if (!messages?.length) {
      return new Response(JSON.stringify({ error: 'No messages provided' }), { status: 400 });
    }

    const pollinationsMessages = [
      { role: "system", content: SUPPORT_CONTEXT },
      ...messages.map((m: any) => ({
        role: m.role === 'bot' ? 'assistant' : 'user',
        content: m.text
      }))
    ];

    const res = await fetch('https://text.pollinations.ai/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: pollinationsMessages, model: "openai" })
    });

    if (!res.ok) throw new Error('API Error');
    const text = await res.text();

    return new Response(JSON.stringify({ text }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Failed to fetch AI' }), { status: 500 });
  }
}
