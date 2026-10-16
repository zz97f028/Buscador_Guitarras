import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import servidor


class ServidorTests(unittest.TestCase):
    @staticmethod
    def web_response(text: str, annotations: list[SimpleNamespace]) -> SimpleNamespace:
        return SimpleNamespace(
            output_text=text,
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(type="output_text", annotations=annotations),
                    ],
                ),
            ],
        )

    def test_documents_supports_page_filters(self) -> None:
        result = servidor.documentos(marca="tAyLoR", tipo="acustica")

        self.assertEqual(result.total, 2)
        self.assertEqual(
            {document.id for document in result.documentos},
            {"HIS-1231223", "DEMO-011"},
        )
        self.assertIsNone(result.documentos[0].anio)
        self.assertEqual(
            result.documentos[0].url,
            "https://www.hispasonic.com/anuncios/guitarra-taylor-ad11-gt-blacktop-nueva/1231223",
        )

    def test_question_performs_web_search_and_returns_unique_sources(self) -> None:
        citations = [
            SimpleNamespace(
                type="url_citation",
                url="https://www.hispasonic.com/anuncios/guitarra/123",
                title="Guitarra de segunda mano",
            ),
            SimpleNamespace(
                type="url_citation",
                url="https://www.hispasonic.com/anuncios/guitarra/123",
                title="Guitarra de segunda mano",
            ),
            SimpleNamespace(
                type="url_citation",
                url="javascript:alert(1)",
                title="Invalid citation",
            ),
            SimpleNamespace(
                type="url_citation",
                url="https://www.guitarristas.info/anuncios/guitarra/456",
                title="Guitarra eléctrica",
            ),
        ]
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=Mock(
                    return_value=self.web_response(
                        "He encontrado anuncios. citeturn0search0", citations
                    )
                ),
            ),
        )
        question = servidor.PreguntaRequest(
            pregunta="Guitarra Gibson Les Paul usada",
            historial=[servidor.Mensaje(role="user", content="Busco guitarra")],
        )
        with patch("servidor.CLIENT", fake_client):
            result = servidor._answer(question)

        self.assertEqual(len(result.fuentes), 2)
        self.assertEqual(result.fuentes[0].portal, "hispasonic.com")
        self.assertEqual(result.fuentes[0].id, "WEB-01")
        self.assertEqual(result.fuentes[1].id, "WEB-02")
        self.assertNotIn("cite", result.respuesta)
        call = fake_client.responses.create.call_args.kwargs
        self.assertEqual(
            call["tools"],
            [{"type": "web_search", "search_context_size": "medium"}],
        )
        self.assertEqual(call["tool_choice"], "required")
        self.assertIn(question.pregunta, call["input"])

    def test_question_without_cited_results_returns_no_results_message(self) -> None:
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=Mock(
                    return_value=self.web_response(
                        "No encontré anuncios.",
                        [],
                    )
                )
            ),
        )
        with (
            patch("servidor.CLIENT", fake_client),
            TestClient(servidor.app) as client,
        ):
            response = client.post(
                "/api/preguntar",
                json={"pregunta": "Guitarra de segunda mano", "historial": []},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["respuesta"], servidor.NO_WEB_RESULTS)
        self.assertEqual(body["fuentes"], [])
        fake_client.responses.create.assert_called_once()

    def test_documents_endpoint_includes_saved_listing_url(self) -> None:
        with TestClient(servidor.app) as client:
            response = client.get("/api/documentos", params={"marca": "Taylor"})

        self.assertEqual(response.status_code, 200)
        document = response.json()["documentos"][0]
        self.assertIsNone(document["anio"])
        self.assertEqual(
            document["url"],
            "https://www.hispasonic.com/anuncios/guitarra-taylor-ad11-gt-blacktop-nueva/1231223",
        )

    def test_twenty_demo_documents_are_explicitly_fictional_and_unlinked(self) -> None:
        with TestClient(servidor.app) as client:
            response = client.get("/api/documentos", params={"portal": "Datos ficticios"})

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["total"], 20)
        self.assertTrue(all(document["ficticio"] for document in result["documentos"]))
        self.assertTrue(all(document["url"] is None for document in result["documentos"]))

        saved = servidor.documentos()
        self.assertEqual(saved.total, 21)
        self.assertEqual(
            sum(document.ficticio for document in saved.documentos),
            20,
        )


if __name__ == "__main__":
    unittest.main()
