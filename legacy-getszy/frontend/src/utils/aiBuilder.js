const API = process.env.REACT_APP_API_URL || 'http://localhost:8001';

export async function generateWithAI({ prompt, type, onChunk }) {
  const token = localStorage.getItem('getszy_token');
  
  const res = await fetch(`${API}/admin/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: getSystemPrompt(type) },
        { role: 'user', content: prompt }
      ],
      stream: true,
    }),
  });

  if (!res.ok) throw new Error(`AI generation failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let full = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
    for (const line of lines) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      try {
        const parsed = JSON.parse(data);
        const token = parsed.choices?.[0]?.delta?.content || '';
        full += token;
        onChunk?.(full);
      } catch {}
    }
  }
  return full;
}

function getSystemPrompt(type) {
  const prompts = {
    dashboard: "You are a React dashboard builder. Generate a complete React component for a dashboard. Use Tailwind CSS for styling. Include real data fetching from APIs. Return ONLY the component code, no explanation.",
    email: "You are an email template builder. Generate a complete responsive HTML email template with inline CSS. Include header, body, CTA button, and footer. Return ONLY the HTML code.",
    landing: "You are a landing page builder. Generate a complete React component for a high-converting landing page. Use Tailwind CSS. Include hero, features, testimonials, CTA sections. Return ONLY the component code.",
    database: "You are a database schema builder. Generate a complete MongoDB/Mongoose schema based on the user's requirements. Include fields, types, validation, indexes, and timestamps. Return ONLY the schema code.",
    api: "You are an API endpoint builder. Generate a complete FastAPI/Express route with CRUD operations, validation, error handling, and auth middleware. Return ONLY the code.",
    video: "You are a video content planner. Generate a detailed video script with scenes, timestamps, visual descriptions, voiceover text, and background music suggestions. Return formatted markdown.",
    chatbot: "You are a chatbot builder. Generate a complete React chatbot component with message handling, typing indicators, quick replies, and API integration. Use Tailwind CSS. Return ONLY the component code.",
    automation: "You are a workflow automation builder. Generate a complete automation workflow in JSON format with triggers, conditions, and actions. Return ONLY the JSON.",
    report: "You are a report builder. Generate a complete React component for a data report with charts (using recharts), tables, filters, and export functionality. Return ONLY the component code.",
    site: "You are a website builder. Generate a complete multi-section website React component with navigation, hero, features, pricing, FAQ, and footer. Use Tailwind CSS. Return ONLY the component code.",
    workflow: "You are a workflow designer. Generate a complete React component for a visual workflow editor with drag-and-drop nodes, connections, and property panels. Use Tailwind CSS. Return ONLY the component code.",
  };
  return prompts[type] || prompts.dashboard;
}

export function downloadFile(content, filename, type = 'text') {
  const mimeTypes = {
    jsx: 'text/javascript',
    html: 'text/html',
    json: 'application/json',
    css: 'text/css',
    md: 'text/markdown',
  };
  const blob = new Blob([content], { type: mimeTypes[type] || 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text) {
  return navigator.clipboard.writeText(text);
}
