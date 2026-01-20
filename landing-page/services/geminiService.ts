import { GoogleGenAI } from "@google/genai";

const getClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API Key not found");
  }
  return new GoogleGenAI({ apiKey });
};

export const generateHeroVisual = async (): Promise<string> => {
  try {
    const ai = getClient();
    // Using Gemini 2.5 Flash Image (Nano Banana) to ensure compatibility and avoid 403 errors
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash-image',
      contents: {
        parts: [
          {
            text: 'Abstract, dark, futuristic, glassmorphism, cyber security shield, data flow, purple and cyan neon lights, linear style landing page background, 4k resolution, minimalistic, sleek, high tech.',
          },
        ],
      },
      config: {
        imageConfig: {
          aspectRatio: "16:9",
          // imageSize is not supported in the flash-image model
        }
      },
    });

    for (const part of response.candidates?.[0]?.content?.parts || []) {
      if (part.inlineData) {
        return `data:image/png;base64,${part.inlineData.data}`;
      }
    }
    throw new Error("No image data returned");
  } catch (error) {
    console.error("Failed to generate image:", error);
    throw error;
  }
};