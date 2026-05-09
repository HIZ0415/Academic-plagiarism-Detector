from types import SimpleNamespace

from django.test import SimpleTestCase

from core.views import views_paper


class PaperResultViewHelperTests(SimpleTestCase):
    def test_build_aigc_result_from_ai_uses_persisted_ai_payload(self):
        task = SimpleNamespace(id=7)
        result = views_paper._build_aigc_result_from_ai(
            task,
            {
                "results": [
                    {
                        "overall_confidence": 0.42,
                        "summary": "done",
                        "details": {
                            "paper_summary": {
                                "risk_level": "low",
                                "overall_risk_score": 0.42,
                                "summary_text": "done",
                            },
                            "paragraph_risks": [
                                {
                                    "index": 1,
                                    "risk_score": 0.42,
                                    "risk_level": "low",
                                    "excerpt": "paragraph",
                                }
                            ],
                            "basic_explanation": ["ok"],
                        },
                    }
                ]
            },
        )

        self.assertEqual(result["task_id"], 7)
        self.assertEqual(result["overall_risk_level"], "low")
        self.assertEqual(result["paragraphs"][0]["index"], 1)

    def test_build_resource_result_detects_doi_without_import_error(self):
        task = SimpleNamespace(id=8)
        result = views_paper._build_resource_result(
            task,
            "References\n[1] Example Author. Example paper. doi 10.1234/example.paper",
        )

        self.assertEqual(result["task_id"], 8)
        self.assertGreaterEqual(result["doi_found_count"], 1)

if __name__ == "__main__":
    import pickle
    import matplotlib.pyplot as plt

    with open('result.pkl', 'rb') as f:
        result = pickle.load(f)
        print()

        img = result[1][1]
        img = result[3][1]
        img = result[4][1][0]
        img = img.astype('uint8')
        print(img.shape)

        plt.imshow(img)#, cmap='gray')  # 不指定 cmap 时默认是 viridis，这里用 gray 更直观
        plt.axis('off')  # 关闭坐标轴
        plt.show()

        # 按照原尺寸保存图片
        plt.imsave('test.png', img)
