import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("WAREHOUSE_DATABASE_URL", "postgresql://unused")

from src import collect


def page(size, total=None, start=0):
    response = Mock()
    response.json.return_value = {
        "data": [{"id": index, "type": "vacancy_type_effective", "description": "Descrição da vaga"} for index in range(start, start + size)]
    }
    if total is not None:
        response.json.return_value["pagination"] = {"total": total}
    return response


class GupyPaginationTests(unittest.TestCase):
    def test_stops_at_cap_or_empty_page_even_with_inaccurate_total(self):
        cases = [
            ([page(100, 100), page(100, 100, start=100), page(50, 100, start=200), page(0, 100)], 250, [0, 100, 200, 250]),
            ([page(100, 900, start=offset) for offset in range(0, 500, 100)], 500, [0, 100, 200, 300, 400]),
            ([page(100), page(20, start=100), page(0)], 120, [0, 100, 120]),
            ([page(0, 0)], 0, [0]),
        ]
        for responses, expected, offsets in cases:
            with self.subTest(expected=expected), patch.object(collect, "KEYWORDS", ["dados"]), \
                    patch.object(collect.requests.Session, "get", side_effect=responses) as get, \
                    patch.object(collect.time, "sleep") as sleep:
                jobs = collect._fetch_gupy(collect.requests.Session())
                self.assertEqual(len(jobs), expected)
                self.assertEqual([call.kwargs["params"]["offset"] for call in get.call_args_list], offsets)
                self.assertEqual(sleep.call_count, len(responses) - 1)
                if jobs:
                    self.assertEqual(jobs[0]["tipo_contrato"], "vacancy_type_effective")
                    self.assertEqual(jobs[0]["descricao"], "Descrição da vaga")

    def test_failure_keeps_previous_pages_and_continues_next_keyword(self):
        responses = [page(100, 200), collect.requests.RequestException("falha"), page(1, 1), page(0, 1)]
        with patch.object(collect, "KEYWORDS", ["a", "b"]), \
                patch.object(collect.requests.Session, "get", side_effect=responses) as get, \
                patch.object(collect.time, "sleep"):
            self.assertEqual(len(collect._fetch_gupy(collect.requests.Session())), 101)
            self.assertEqual(get.call_args.kwargs["params"]["jobName"], "b")

    def test_repeated_page_stops_and_seen_ids_reset_for_next_keyword(self):
        responses = [page(100), page(100), page(1), page(0)]
        with patch.object(collect, "KEYWORDS", ["a", "b"]), \
                patch.object(collect.requests.Session, "get", side_effect=responses) as get, \
                patch.object(collect.time, "sleep") as sleep, \
                self.assertLogs(collect.logger, level="WARNING") as logs:
            self.assertEqual(len(collect._fetch_gupy(collect.requests.Session())), 101)
            self.assertEqual(get.call_count, 4)
            self.assertEqual(sleep.call_count, 2)
            self.assertIn("página sem IDs novos", logs.output[0])

    def test_partially_repeated_page_continues_when_it_has_new_ids(self):
        responses = [page(2), page(2, start=1), page(0)]
        with patch.object(collect, "KEYWORDS", ["dados"]), \
                patch.object(collect.requests.Session, "get", side_effect=responses) as get, \
                patch.object(collect.time, "sleep"):
            self.assertEqual(len(collect._fetch_gupy(collect.requests.Session())), 4)
            self.assertEqual([call.kwargs["params"]["offset"] for call in get.call_args_list], [0, 2, 4])


class MainTests(unittest.TestCase):
    def test_empty_collection_never_connects_to_database(self):
        with patch.object(collect, "_fetch_gupy", return_value=[]), patch.object(collect, "save_to_postgres") as save:
            with self.assertRaises(RuntimeError):
                collect.main()
            save.assert_not_called()

    def test_main_passes_only_unique_jobs_to_load(self):
        jobs = [{"id": "gupy_1"}, {"id": "gupy_1"}, {"id": "gupy_2"}]
        with patch.object(collect, "_fetch_gupy", return_value=jobs), patch.object(collect, "save_to_postgres") as save:
            collect.main()
            save.assert_called_once_with([jobs[0], jobs[2]])


if __name__ == "__main__":
    unittest.main()
