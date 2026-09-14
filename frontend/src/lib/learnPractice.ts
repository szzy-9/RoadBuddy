import type { MockTestAnswer, MockTestQuestion } from '../types/api'

/** Only submit a complete set of answers for the questions in this test. */
export function getMockTestAnswers(
  questions: readonly Pick<MockTestQuestion, 'id'>[],
  selectedOptions: Readonly<Record<string, string>>,
): MockTestAnswer[] | null {
  if (questions.length === 0 || questions.some((question) => !selectedOptions[question.id])) {
    return null
  }
  return questions.map((question) => ({
    question_id: question.id,
    selected_option: selectedOptions[question.id],
  }))
}
