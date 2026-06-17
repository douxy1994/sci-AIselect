import inspect
import importlib
import unittest

import scripts.journal_metrics as metrics
selector = importlib.import_module("scripts.select_journals")
full_workflow = importlib.import_module("scripts.full_workflow")
journal_learner = importlib.import_module("scripts.journal_learner")
from scripts.select_journals import (
    infer_paper_profile,
    rank_metric_records,
    format_selection_report,
    format_selection_matrix,
    interleave_candidate_groups,
    assign_submission_bands,
)
from scripts.journal_learner import generate_reference_cover_letter


class SciAiselectTests(unittest.TestCase):
    def test_infers_english_groundwater_isotope_categories(self):
        profile = infer_paper_profile(
            "Groundwater nitrate source identification using stable isotopes "
            "and hydrochemistry in an agricultural watershed."
        )

        categories = {(c["category1"], c["category2"]) for c in profile["categories"]}

        self.assertIn(("环境科学与生态学", "水资源"), categories)
        self.assertIn(("地球科学", "地球化学与地球物理"), categories)
        self.assertNotEqual(
            profile["categories"],
            [{"category1": "环境科学与生态学", "category2": "环境科学"}],
        )

    def test_infers_medical_ai_categories(self):
        profile = infer_paper_profile(
            "A deep learning radiomics model predicts lung cancer prognosis "
            "from CT imaging and clinical records."
        )

        categories = {(c["category1"], c["category2"]) for c in profile["categories"]}

        self.assertIn(("医学", "肿瘤学"), categories)
        self.assertIn(("计算机科学", "计算机：人工智能"), categories)

    def test_applied_method_terms_do_not_dominate_domain_terms(self):
        profile = infer_paper_profile(
            "Machine learning model for crop irrigation scheduling in agricultural farmland."
        )

        categories = [(c["category1"], c["category2"]) for c in profile["categories"]]

        self.assertEqual(categories[0], ("农林科学", "农业综合"))
        self.assertNotEqual(categories[0], ("计算机科学", "计算机：人工智能"))
        self.assertIn("machine learning", profile["methods"])

    def test_ranking_uses_fit_quality_and_risk_flags(self):
        profile = infer_paper_profile(
            "Groundwater nitrate source identification using stable isotopes "
            "and hydrochemistry in an agricultural watershed."
        )
        records = [
            {
                "name": "Journal of Hydrology",
                "impact_factor": "6.3",
                "partition": "1区",
                "sci_type": "SCIE",
                "h_index": 198,
                "field": "水资源; 地球化学与地球物理",
                "speed": "网友分享经验：平均8.3个月",
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Broad Environmental Letters",
                "impact_factor": "8.0",
                "partition": "1区",
                "sci_type": "SCIE",
                "h_index": 80,
                "field": "环境科学",
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Emerging Water Reports",
                "impact_factor": "2.1",
                "partition": "4区",
                "sci_type": "ESCI",
                "field": "水资源",
                "_sources": ["letpub"],
                "_source_errors": {"openalex": "timeout"},
            },
        ]

        ranked = rank_metric_records(profile, records)

        self.assertEqual(ranked[0]["name"], "Journal of Hydrology")
        self.assertEqual(ranked[0]["tier"], "推荐")
        self.assertEqual(ranked[-1]["tier"], "谨慎")
        self.assertIn("OpenAlex未获取", ranked[-1]["data_notes"])

    def test_report_does_not_expose_login_or_comment_flow(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "_sources": ["letpub"],
                    "_source_errors": {"openalex": "SSL error"},
                }
            ],
        )

        report = format_selection_report(profile, ranked)

        self.assertIn("sci-aiselect", report)
        self.assertIn("OpenAlex未获取", report)
        self.assertNotIn("评论", report)
        self.assertNotIn("登录", report)
        self.assertNotIn("cookie", report.lower())
        self.assertNotIn("comments_mode", inspect.signature(selector.select_journals).parameters)

    def test_openalex_source_matching_rejects_unrelated_name(self):
        source = {
            "display_name": "Journal of Hydrology",
            "issn_l": "0022-1694",
            "issn": ["0022-1694"],
        }

        self.assertTrue(metrics._openalex_source_matches(source, "Journal of Hydrology"))
        self.assertTrue(metrics._openalex_source_matches(source, "J Hydrol", "00221694"))
        self.assertFalse(metrics._openalex_source_matches(source, "Nature"))

    def test_openalex_source_matching_handles_missing_lists(self):
        source = {
            "display_name": "Journal of Hydrology",
            "issn_l": None,
            "issn": None,
            "alternate_titles": None,
        }

        self.assertTrue(metrics._openalex_source_matches(source, "Journal of Hydrology"))

    def test_matrix_report_shows_decision_table(self):
        profile = infer_paper_profile("groundwater isotope hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Journal of Hydrology",
                    "impact_factor": "6.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源; 地球化学与地球物理",
                    "speed": "网友分享经验：平均8.3个月",
                    "_sources": ["letpub", "openalex"],
                    "h_index": 198,
                    "is_oa": False,
                }
            ],
        )

        matrix = format_selection_matrix(profile, ranked)

        self.assertIn("| 期刊 | 建议 | 主题匹配 |", matrix)
        self.assertIn("Journal of Hydrology", matrix)
        self.assertIn("SCIE", matrix)
        self.assertIn("平均8.3个月", matrix)

    def test_candidate_groups_are_interleaved_across_categories(self):
        groups = [
            [{"name": "Water A"}, {"name": "Water B"}, {"name": "Water C"}],
            [{"name": "Geochem A"}, {"name": "Geochem B"}],
            [{"name": "Geology A"}],
        ]

        candidates = interleave_candidate_groups(groups, limit=5)

        self.assertEqual(
            [c["name"] for c in candidates],
            ["Water A", "Geochem A", "Geology A", "Water B", "Geochem B"],
        )

    def test_review_journal_is_cautious_for_non_review_paper(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry field sampling")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "REVIEWS OF GEOPHYSICS",
                    "impact_factor": "37.3",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "地球化学与地球物理",
                    "_sources": ["letpub", "openalex"],
                }
            ],
        )

        self.assertEqual(ranked[0]["tier"], "谨慎")
        self.assertIn("综述型期刊", "；".join(ranked[0]["risk_reasons"]))

    def test_submission_bands_cover_ambition_solid_and_safe_options(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry")
        ranked = rank_metric_records(
            profile,
            [
                {
                    "name": "Ambition Journal",
                    "impact_factor": "12",
                    "partition": "1区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
                {
                    "name": "Solid Journal",
                    "impact_factor": "5.5",
                    "partition": "2区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
                {
                    "name": "Safe Journal",
                    "impact_factor": "3.2",
                    "partition": "3区",
                    "sci_type": "SCIE",
                    "field": "水资源",
                    "_sources": ["letpub"],
                },
            ],
        )

        banded = assign_submission_bands(ranked)
        report = format_selection_report(profile, banded)

        self.assertEqual([item["submission_band"] for item in banded], ["冲刺", "稳妥", "保底"])
        self.assertIn("未提供全文质量评价", report)

    def test_fast_review_preference_changes_ranking(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry")
        records = [
            {
                "name": "Fast Water Journal",
                "impact_factor": "5.5",
                "partition": "2区",
                "sci_type": "SCIE",
                "h_index": 80,
                "field": "水资源",
                "speed": "期刊官网数据：Time to first decision: 5 days; Review time: 28 days; Submission to acceptance: 45 days",
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Slow Elite Water Journal",
                "impact_factor": "8.5",
                "partition": "1区",
                "sci_type": "SCIE",
                "h_index": 160,
                "field": "水资源",
                "speed": "网友分享经验：平均8.3个月",
                "_sources": ["letpub", "openalex"],
            },
        ]

        normal = rank_metric_records(profile, records)
        fast_weighted = rank_metric_records(
            profile,
            records,
            preferences={"review_speed_priority": True},
        )

        self.assertEqual(normal[0]["name"], "Slow Elite Water Journal")
        self.assertEqual(fast_weighted[0]["name"], "Fast Water Journal")
        self.assertGreater(fast_weighted[0]["review_speed_score"], 0)

    def test_wos_on_hold_records_are_excluded(self):
        profile = infer_paper_profile("groundwater nitrate hydrochemistry")
        records = [
            {
                "name": "On Hold Water Journal",
                "impact_factor": "20",
                "partition": "1区",
                "sci_type": "SCIE",
                "field": "水资源",
                "raw_data": {"source": "wos", "status": "Web of Science Core Collection: On Hold"},
                "_sources": ["letpub", "openalex"],
            },
            {
                "name": "Active Water Journal",
                "impact_factor": "4.5",
                "partition": "2区",
                "sci_type": "SCIE",
                "field": "水资源",
                "_sources": ["letpub", "openalex"],
            },
        ]

        ranked = rank_metric_records(profile, records)

        self.assertEqual([item["name"] for item in ranked], ["Active Water Journal"])

    def test_apc_line_uses_doaj_price_and_cny_rate(self):
        original_rate = metrics._get_cny_rate
        metrics._get_cny_rate = lambda currency: {"rate": 7.1, "date": "2026-06-17"}
        try:
            profile = infer_paper_profile("groundwater nitrate hydrochemistry")
            ranked = rank_metric_records(
                profile,
                [
                    {
                        "name": "APC Water Journal",
                        "impact_factor": "5.5",
                        "partition": "2区",
                        "sci_type": "SCIE",
                        "field": "水资源",
                        "doaj_apc": {
                            "has_apc": True,
                            "max": [{"price": 1995, "currency": "USD"}],
                        },
                        "_sources": ["doaj", "openalex"],
                    }
                ],
            )
            report = format_selection_report(profile, ranked)
        finally:
            metrics._get_cny_rate = original_rate

        self.assertEqual(ranked[0]["apc_source"], "DOAJ")
        self.assertIn("USD 1995", report)
        self.assertIn("RMB 14164", report)

    def test_full_workflow_accepts_review_preference_without_live_network(self):
        original_finders = full_workflow.search_all_journal_finders
        original_search = full_workflow.advanced_search
        original_metrics = full_workflow.get_journal_metrics_safe
        try:
            full_workflow.search_all_journal_finders = lambda *args, **kwargs: []
            full_workflow.advanced_search = lambda **kwargs: {
                "journals": [{"name": "Fast Water Journal"}]
            }
            full_workflow.get_journal_metrics_safe = lambda name: {
                "name": name,
                "impact_factor": "5.5",
                "partition": "2区",
                "sci_type": "SCIE",
                "h_index": 80,
                "field": "水资源",
                "speed": "期刊官网数据：Time to first decision: 5 days; Submission to acceptance: 45 days",
                "_sources": ["letpub", "openalex"],
            }

            bundle = full_workflow.select_journals_with_finder(
                title="Groundwater nitrate hydrochemistry",
                abstract="This study examines groundwater nitrate using hydrochemistry.",
                keywords=["groundwater"],
                use_journal_finders=False,
                review_preference=True,
            )
        finally:
            full_workflow.search_all_journal_finders = original_finders
            full_workflow.advanced_search = original_search
            full_workflow.get_journal_metrics_safe = original_metrics

        self.assertTrue(bundle["review_speed_priority"])
        self.assertEqual(bundle["results"][0]["name"], "Fast Water Journal")
        self.assertGreater(bundle["results"][0]["review_speed_score"], 0)

    def test_cover_letter_follows_template_and_disclaims_verification(self):
        cover_letter = generate_reference_cover_letter(
            title="Groundwater nitrate source identification using stable isotopes",
            abstract=(
                "Groundwater nitrate pollution threatens agricultural watersheds. "
                "This study uses stable isotopes and hydrochemistry to identify nitrate sources. "
                "The results reveal dominant fertilizer and manure contributions with implications for water management."
            ),
            journal_info={
                "name": "Journal of Hydrology",
                "aim_scope": "The journal publishes hydrology, water resources, and environmental research.",
                "style_analysis": {"common_title_words": ["water", "hydrology"]},
            },
        )

        self.assertIn("仅供参考", cover_letter)
        self.assertIn("不对内容是否合理和真实负责", cover_letter)
        self.assertIn("Dear Editor,", cover_letter)
        self.assertIn("Groundwater nitrate source identification using stable isotopes", cover_letter)
        self.assertIn("Journal of Hydrology", cover_letter)
        self.assertIn("hydrology", cover_letter)
        self.assertIn("merit external review", cover_letter)
        self.assertIn("readership", cover_letter)
        self.assertIn("topical fit", cover_letter)
        self.assertIn("Please verify before use", cover_letter)
        self.assertIn("Sincerely", cover_letter)
        self.assertIn("XXXXX", cover_letter)
        self.assertNotIn("[Title]", cover_letter)
        self.assertNotIn("[Journal]", cover_letter)


if __name__ == "__main__":
    unittest.main()
