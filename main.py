import os
import re
import threading
import uuid
from urllib.parse import quote

import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


APP_TITLE = "IA Ahmad"
HF_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"
POLLINATIONS_URL = "https://gen.pollinations.ai/image/"

SYSTEM_PROMPT = """
Tu es IA Ahmad, l'assistant personnel d'Ahmad.
Tu aides principalement en programmation, Python, Kivy, Android,
GitHub et dans ses projets informatiques.
Réponds clairement en français, avec des explications adaptées et du code
complet quand c'est utile. N'affirme jamais qu'un code a été testé si ce n'est
pas le cas.

Si Ahmad demande de créer, dessiner ou générer une image, réponds uniquement
avec cette forme exacte :
IMAGE_PROMPT: followed by a detailed visual description in English.
N'ajoute aucun texte avant ou après cette ligne pour une demande d'image.
Pour toutes les autres demandes, réponds normalement en français.
""".strip()


class MessageBubble(BoxLayout):
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(0.86, None),
            padding=(dp(12), dp(10)),
            **kwargs
        )
        self.is_user = is_user
        self.height = dp(60)

        with self.canvas.before:
            self._bg_color = Color(
                0.10, 0.34, 0.57, 1
            ) if is_user else Color(0.14, 0.17, 0.24, 1)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)]
            )

        self.bind(pos=self._update_bg, size=self._update_bg)

        self.label = Label(
            text=text,
            markup=False,
            color=(0.96, 0.97, 1, 1),
            font_size="15sp",
            halign="left",
            valign="top",
            size_hint=(1, None),
            text_size=(WindowWidth() * 0.78, None),
        )
        self.label.bind(texture_size=self._label_resized)
        self.bind(width=self._update_text_width)
        self.add_widget(self.label)
        self.label.texture_update()
        self._label_resized(self.label, self.label.texture_size)

    def _update_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _update_text_width(self, *_):
        self.label.text_size = (max(dp(80), self.width - dp(24)), None)

    def _label_resized(self, label, size):
        label.height = size[1] + dp(2)
        self.height = label.height + dp(20)


def WindowWidth():
    from kivy.core.window import Window
    return max(dp(160), Window.width * 0.78)


class IAAhmadApp(App):
    def build(self):
        self.title = APP_TITLE
        self.hf_token = ""
        self.pollinations_key = ""
        self.busy = False
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        header = BoxLayout(
            size_hint_y=None,
            height=dp(52),
            spacing=dp(8)
        )
        title = Label(
            text="[b]IA AHMAD[/b]",
            markup=True,
            font_size="21sp",
            color=(0.35, 0.72, 1, 1),
            halign="left",
            valign="middle"
        )
        title.bind(size=lambda obj, val: setattr(obj, "text_size", val))
        settings_button = Button(
            text="Clés API",
            size_hint_x=None,
            width=dp(92)
        )
        settings_button.bind(on_release=self.open_settings)
        header.add_widget(title)
        header.add_widget(settings_button)
        root.add_widget(header)

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4),
            scroll_type=["bars", "content"]
        )
        self.chat = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=(dp(2), dp(8))
        )
        self.chat.bind(minimum_height=self.chat.setter("height"))
        self.scroll.add_widget(self.chat)
        root.add_widget(self.scroll)

        bottom = BoxLayout(
            size_hint_y=None,
            height=dp(56),
            spacing=dp(8)
        )
        self.message_input = TextInput(
            hint_text="Écris ton message...",
            multiline=False,
            font_size="16sp",
            padding=(dp(12), dp(15)),
            background_color=(0.13, 0.15, 0.21, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.6, 0.62, 0.68, 1),
            cursor_color=(0.3, 0.7, 1, 1)
        )
        self.message_input.bind(on_text_validate=self.send_message)

        self.send_button = Button(
            text="Envoyer",
            size_hint_x=None,
            width=dp(100)
        )
        self.send_button.bind(on_release=self.send_message)
        bottom.add_widget(self.message_input)
        bottom.add_widget(self.send_button)
        root.add_widget(bottom)

        self.add_message(
            "IA Ahmad",
            "Salut Ahmad ! Ajoute tes clés API avec le bouton « Clés API » "
            "pour commencer. Les clés restent en mémoire pendant cette session."
        )
        return root

    def open_settings(self, *_):
        panel = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(12)
        )
        panel.add_widget(Label(
            text="Jeton Hugging Face (nécessaire pour discuter)",
            size_hint_y=None,
            height=dp(38)
        ))
        hf_input = TextInput(
            text=self.hf_token,
            password=True,
            multiline=False,
            hint_text="hf_...",
            size_hint_y=None,
            height=dp(46)
        )
        panel.add_widget(hf_input)

        panel.add_widget(Label(
            text="Clé Pollinations (facultative, pour les images)",
            size_hint_y=None,
            height=dp(38)
        ))
        poll_input = TextInput(
            text=self.pollinations_key,
            password=True,
            multiline=False,
            hint_text="Clé autorisée Pollinations",
            size_hint_y=None,
            height=dp(46)
        )
        panel.add_widget(poll_input)

        note = Label(
            text=(
                "Les clés ne sont pas enregistrées dans GitHub ni dans un fichier. "
                "Ne partage pas cette APK avec tes clés personnelles."
            ),
            size_hint_y=None,
            height=dp(62),
            font_size="12sp",
            color=(0.75, 0.78, 0.84, 1)
        )
        panel.add_widget(note)

        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        cancel = Button(text="Fermer")
        save = Button(text="Enregistrer")
        buttons.add_widget(cancel)
        buttons.add_widget(save)
        panel.add_widget(buttons)

        popup = Popup(
            title="Configuration de IA Ahmad",
            content=panel,
            size_hint=(0.92, None),
            height=dp(390),
            auto_dismiss=False
        )
        cancel.bind(on_release=popup.dismiss)

        def save_keys(*_):
            self.hf_token = hf_input.text.strip()
            self.pollinations_key = poll_input.text.strip()
            popup.dismiss()
            self.add_message(
                "IA Ahmad",
                "Configuration mise à jour. Les clés seront oubliées "
                "à la fermeture de l'application."
            )

        save.bind(on_release=save_keys)
        popup.open()

    def add_message(self, author, text, is_user=False):
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(4)
        )
        bubble = MessageBubble(text, is_user=is_user)
        if is_user:
            row.add_widget(Widget())
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Widget())

        bubble.bind(height=lambda obj, value: setattr(row, "height", value))
        self.chat.add_widget(row)
        Clock.schedule_once(lambda _dt: self.scroll_to_bottom(), 0.15)

    def add_image(self, image_path):
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(280),
            spacing=dp(4)
        )
        image = AsyncImage(
            source=image_path,
            size_hint=(0.86, 1),
            allow_stretch=True,
            keep_ratio=True
        )
        row.add_widget(image)
        row.add_widget(Widget())
        self.chat.add_widget(row)
        Clock.schedule_once(lambda _dt: self.scroll_to_bottom(), 0.15)

    def scroll_to_bottom(self):
        self.scroll.scroll_y = 0

    def send_message(self, *_):
        if self.busy:
            return

        prompt = self.message_input.text.strip()
        if not prompt:
            return

        if not self.hf_token:
            self.add_message(
                "IA Ahmad",
                "Ajoute d'abord ton jeton Hugging Face avec le bouton « Clés API »."
            )
            return

        self.message_input.text = ""
        self.add_message("Ahmad", prompt, is_user=True)
        self.history.append({"role": "user", "content": prompt})

        messages = [self.history[0]] + self.history[-12:]
        self.busy = True
        self.send_button.disabled = True
        self.send_button.text = "..."

        threading.Thread(
            target=self.network_worker,
            args=(messages,),
            daemon=True
        ).start()

    def network_worker(self, messages):
        try:
            headers = {
                "Authorization": "Bearer " + self.hf_token,
                "Content-Type": "application/json"
            }
            payload = {
                "model": HF_MODEL,
                "messages": messages,
                "max_tokens": 1200,
                "temperature": 0.5,
                "stream": False
            }

            response = requests.post(
                HF_URL,
                headers=headers,
                json=payload,
                timeout=(20, 150)
            )
            if not response.ok:
                detail = response.text[:500]
                raise RuntimeError(
                    "Hugging Face a répondu HTTP "
                    + str(response.status_code) + " : " + detail
                )

            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            if isinstance(answer, list):
                answer = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in answer
                )
            answer = str(answer).strip()
            if not answer:
                raise RuntimeError("Le modèle a renvoyé une réponse vide.")

            if answer.startswith("IMAGE_PROMPT:"):
                image_prompt = answer.split(":", 1)[1].strip()
                if not image_prompt:
                    raise RuntimeError("La description de l'image est vide.")
                self.generate_image(image_prompt)
                self.history.append({
                    "role": "assistant",
                    "content": "IMAGE_PROMPT: " + image_prompt
                })
            else:
                self.history.append({"role": "assistant", "content": answer})
                Clock.schedule_once(
                    lambda _dt, text=answer: self.add_message("IA Ahmad", text)
                )

        except requests.exceptions.Timeout:
            self.show_error("Le serveur a mis trop de temps à répondre.")
        except requests.exceptions.RequestException as exc:
            self.show_error("Erreur réseau : " + str(exc))
        except (KeyError, IndexError, ValueError) as exc:
            self.show_error("Réponse API inattendue : " + str(exc))
        except Exception as exc:
            self.show_error(str(exc))
        finally:
            Clock.schedule_once(self.finish_request)

    def generate_image(self, prompt):
        if not self.pollinations_key:
            raise RuntimeError(
                "La clé Pollinations manque. Ajoute-la dans « Clés API » "
                "puis renvoie ta demande d'image."
            )

        url = POLLINATIONS_URL + quote(prompt, safe="")
        headers = {"Authorization": "Bearer " + self.pollinations_key}

        response = requests.get(
            url,
            headers=headers,
            params={"model": "flux", "width": 768, "height": 768},
            timeout=(20, 180),
            stream=True
        )
        if not response.ok:
            detail = response.text[:300]
            raise RuntimeError(
                "Pollinations a répondu HTTP "
                + str(response.status_code) + " : " + detail
            )

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            response.close()
            raise RuntimeError("Pollinations n'a pas renvoyé un fichier image.")

        extension = ".jpg" if "jpeg" in content_type else ".png"
        image_path = os.path.join(
            self.user_data_dir, "generated_" + uuid.uuid4().hex + extension
        )

        total = 0
        try:
            with open(image_path, "wb") as output:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > 12 * 1024 * 1024:
                        raise RuntimeError("L'image dépasse la limite de 12 Mo.")
                    output.write(chunk)
        finally:
            response.close()

        Clock.schedule_once(
            lambda _dt, path=image_path: self.show_image(path)
        )

    def show_image(self, image_path):
        self.add_message("IA Ahmad", "Voici l'image générée :")
        self.add_image(image_path)

    def show_error(self, message):
        Clock.schedule_once(
            lambda _dt, text=message: self.add_message("Erreur", text)
        )

    def finish_request(self, _dt):
        self.busy = False
        self.send_button.disabled = False
        self.send_button.text = "Envoyer"


if __name__ == "__main__":
    IAAhmadApp().run()
