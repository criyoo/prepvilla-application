export type LearningCardImageKey = "choose" | "exchange" | "progress";

const chooseOne = "/images/challenge.webp";

export const LEARNING_CARD_IMAGES: Record<LearningCardImageKey, string[]> = {
  choose: [chooseOne, chooseOne],
  exchange: [chooseOne, chooseOne],
  progress: [chooseOne, chooseOne],
};
