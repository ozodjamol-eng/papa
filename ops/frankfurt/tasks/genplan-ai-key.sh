#!/usr/bin/env bash
# УСТАРЕЛА (30.10.2026, сверка): аккаунт Anthropic владельца заблокирован — ключ Claude поставить нельзя.
# ИИ GENPLAN работает на Gemini (ключ — задача genplan-gemini-key). Задача ничего не меняет на сервере.
# Прежняя версия (ключ Anthropic → /etc/papa-genplan/ai.env, AI_PRIMARY=claude) — в истории git.
echo "Задача genplan-ai-key устарела: аккаунт Anthropic заблокирован, ИИ GENPLAN работает на Gemini."
echo "Ключ Gemini — задача genplan-gemini-key. Ничего не изменено."
echo "== AI_KEY_SKIPPED"
exit 0
