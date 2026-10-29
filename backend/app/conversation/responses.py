"""Local response generation: template banks keyed by situation, filled with topics and cues."""
from __future__ import annotations

import random

from app.schemas import Analysis

T = {
 "greeting": ["Hi there! How's your day going?", "Hello! What's on your mind today?", "Hey! Good to see you. How are you feeling?"],
 "farewell": ["Take care! Come back any time.", "Goodbye for now. I hope the rest of your day goes well.", "See you later. Look after yourself!"],
 "gratitude": ["You're welcome! Is there anything else you'd like to talk through?", "Glad that helped. How are you feeling now?", "Happy to be here for it. Anything else on your mind?"],
 "question": [
    "Good question. In local mode I can't look things up or reason deeply, but I can reflect on how you feel about it. What's behind the question for you?",
    "I can't search for facts offline, so I won't guess. Tell me more about {topic} and I'll help you think it through.",
    "That's something I can't answer reliably without an AI provider or lookup. What would a good answer change for you?"],
 "good_news": [
    "Congratulations on {topic}! That's wonderful news. How are you celebrating?",
    "That's great news about {topic}. It sounds like your effort paid off. What are you most proud of?",
    "Well done! {topic_cap} clearly mattered, and this is a real win. What's next?",
    "That's fantastic! Take a moment to enjoy it. How did it feel when you found out?",
    "Wonderful, congratulations! What helped you get there?"],
 "excitement": [
    "I love that energy! What are you most excited about with {topic}?",
    "That sounds really joyful. Tell me more about {topic}.",
    "Great to hear you're feeling this good! What made it special?",
    "That happiness comes through. What would make it even better?"],
 "frustration": [
    "That sounds really frustrating, especially after the effort you put into {topic}. What part is weighing on you most?",
    "I'm sorry, that's disappointing. Wanting {topic} to go differently makes complete sense. What happened?",
    "That sounds unfair and discouraging. Do you want to vent, or think about what comes next?",
    "I hear how upsetting this is. Would it help to talk through what went wrong?",
    "That's a tough outcome. What do you need most right now?"],
 "sadness_stress": [
    "That sounds heavy, and it's understandable to feel this way about {topic}. What's been hardest?",
    "Thanks for telling me. Feeling this way around {topic} is human. Would it help to break it into smaller pieces?",
    "I'm sorry you're dealing with this. What would feel like a small bit of relief right now?",
    "That sounds stressful. Have you been able to talk to someone you trust about it?",
    "I hear you. Do you want to talk about what's behind this feeling?"],
 "encouragement": [
    "You've got more strength than you may feel right now. What's one small step you could take today?",
    "Hard stretches don't last forever, and reaching out is a good sign. What would help most right now?",
    "I believe you can get through this, one step at a time. Want to tell me what's making it hard?"],
 "mixed": [
    "It sounds like two things are true at once: \"{pos}\" feels good, while \"{neg}\" is on your mind. Which one is louder right now?",
    "I'm hearing both sides: something positive (\"{pos}\") and something concerning (\"{neg}\"). Both can be real. What would help with the harder part?",
    "That's a mix: \"{pos}\" alongside \"{neg}\". Mixed feelings about {topic} are very normal. Want to unpack either?"],
 "general_positive": [
    "That sounds good! Tell me more about {topic}.",
    "Nice, I'm glad. What was the best part?",
    "That's lovely to hear. What made it work so well?"],
 "general_negative": [
    "That doesn't sound great. What happened with {topic}?",
    "I'm sorry to hear that. Do you want to talk about it?",
    "That sounds rough. What would help right now?"],
 "general_neutral": [
    "Thanks for sharing. How do you feel about {topic}?",
    "Got it. Is there something about {topic} you'd like to explore?",
    "Okay. What would you like to talk about next?",
    "I see. Is this something on your mind, or just an update?"],
 "uncertain": [
    "I'm not fully sure how you feel about that; the signals are mixed or weak. Could you say a bit more?",
    "I can't tell from that alone whether this is good or bad for you. How are you feeling about it?"],
 "unknown": [
    "I didn't quite catch that. Could you rephrase it?",
    "I'm not sure what you mean yet. Can you tell me a little more?",
    "Hmm, I couldn't read that one. What would you like to talk about?"],
}
SHIFT = "That's quite a shift from earlier. "
CONTINUE = "On your earlier point: "


def _topic(a: Analysis) -> tuple[str | None, bool]:
    return (a.topics[0].ref if a.topics else None), bool(a.topics and a.topics[0].from_context)


def build_reply(a: Analysis, recent: list[str], rng: random.Random | None = None) -> tuple[str, str]:
    rng = rng or random.Random()
    intent, s = a.intent.intent, a.sentiment
    topic, from_ctx = _topic(a)
    if intent in ("greeting", "farewell", "gratitude", "encouragement", "unknown", "question"):
        key = intent
    elif s.mixed:
        key = "mixed"
    elif intent in ("good_news", "excitement", "frustration", "sadness_stress"):
        key = intent
    elif s.uncertain and not s.mixed and s.confidence < 0.55:
        key = "uncertain"
    else:
        key = {"positive": "general_positive", "negative": "general_negative"}.get(s.label, "general_neutral")
    options = T[key]
    eligible = [(i, t) for i, t in enumerate(options) if topic or "{topic" not in t]
    fresh = [(i, t) for i, t in eligible if f"{key}:{i}" not in recent] or eligible or list(enumerate(options))
    idx, tpl = rng.choice(fresh)
    pos = next((c.text for c in s.rules.cues if c.polarity == "positive"), "something good")
    neg = next((c.text for c in s.rules.cues if c.polarity == "negative"), "something worrying")
    t_ref = topic or "this"
    text = tpl.format(topic=t_ref, topic_cap=t_ref[0].upper() + t_ref[1:], pos=pos, neg=neg)
    if a.context and a.context.sentiment_shift and key not in ("greeting", "farewell", "gratitude"):
        text = SHIFT + text
    elif from_ctx and key in ("general_neutral", "general_positive", "general_negative"):
        text = CONTINUE + text
    return text, f"{key}:{idx}"
