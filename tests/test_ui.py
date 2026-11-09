"""Headless UI tests with Streamlit's AppTest (no browser needed). Same offline setup as test_core."""
from __future__ import annotations

import unittest

import test_core  # sets temp env, stand-in embeddings; must come before importing app code
from streamlit.testing.v1 import AppTest

APP = str(test_core.ROOT / "app.py")


def setUpModule():
    test_core.setUpModule()


def new_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def team_app() -> AppTest:
    at = new_app()
    at.sidebar.text_input[0].set_value("test").run()  # TEAM_PASSWORD is "test" in the test env
    return at


class TestClientUI(unittest.TestCase):
    def test_renders_without_errors_and_shows_examples(self):
        at = new_app()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual([t.label for t in at.tabs], ["Chat", "Evaluator guide"])
        self.assertEqual(len([b for b in at.main.button if b.key and b.key.startswith("ex")]), 7)

    def test_example_question_gets_an_answer(self):
        at = new_app()
        at.button(key="ex0").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual([m.name for m in at.chat_message], ["user", "assistant"])

    def test_all_sample_questions_listed(self):
        at = new_app()
        more = [b for b in at.main.button if b.key and b.key.startswith("more_")]
        self.assertGreaterEqual(len(more), 20)  # 16 website FAQ + sample-document questions
        more[0].click().run()
        self.assertEqual(len(at.chat_message), 2)

    def test_back_button_returns_to_examples(self):
        at = new_app()
        at.button(key="ex0").click().run()
        self.assertEqual(len(at.chat_message), 2)  # conversation started
        at.button(key="back_to_examples").click().run()
        self.assertEqual(len([b for b in at.main.button if b.key and b.key.startswith("ex")]), 7)
        self.assertEqual(len(at.chat_message), 0)

    def test_client_cannot_see_team_tools(self):
        at = new_app()
        self.assertFalse([b for b in at.sidebar.button if b.label == "Load sample documents"])


    def test_lead_form_validates_and_saves(self):
        at = new_app()
        send = [b for b in at.sidebar.button if b.label == "Send"][0]
        send.click().run()
        self.assertTrue(at.sidebar.error)  # empty form rejected
        by_label = {t.label: t for t in at.sidebar.text_input}
        by_label["Name"].set_value("Test Person")
        by_label["Email"].set_value("test.person@example.com")
        at.sidebar.checkbox[0].check()
        [b for b in at.sidebar.button if b.label == "Send"][0].click().run()
        self.assertTrue(at.sidebar.success, [e.value for e in at.sidebar.error])


class TestTeamUI(unittest.TestCase):
    def test_password_unlocks_team_tabs(self):
        at = team_app()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual([t.label for t in at.tabs], ["Chat", "Evaluator guide", "Leads", "Self-test"])

    def test_wrong_password_stays_client(self):
        at = new_app()
        at.sidebar.text_input[0].set_value("nope").run()
        self.assertEqual(len(at.tabs), 2)

    def test_self_test_all_pass(self):
        at = team_app()
        [b for b in at.main.button if b.label == "Run self-test"][0].click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(at.success and "14/14" in at.success[0].value, [e.value for e in at.error])

    def test_load_samples_button(self):
        at = team_app()
        [b for b in at.sidebar.button if b.label == "Load sample documents"][0].click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(at.sidebar.success)


if __name__ == "__main__":
    unittest.main()
