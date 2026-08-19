"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "../shared/AppHeader";
import { api } from "../shared/api";

type Review = {
  id: string;
  studentName: string;
  rating: number;
  comment: string;
  createdAt: string;
  bookingId: string;
};

type ReviewsResponse = {
  reviews: Review[];
};

export function ReviewsPage({ tutorId, tutorName }: { tutorId: string; tutorName: string }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReviews = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.get<ReviewsResponse>(`/api/tutors/${tutorId}/reviews`);
      if (!response.ok) {
        throw new Error(response.error || "Failed to load reviews");
      }
      setReviews(response.data.reviews);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    } finally {
      setIsLoading(false);
    }
  }, [tutorId]);

  useEffect(() => {
    void loadReviews();
  }, [loadReviews]);

  const averageRating = reviews.length > 0 
    ? reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length 
    : 0;

  const ratingDistribution = [1, 2, 3, 4, 5].map(rating => 
    reviews.filter(review => review.rating === rating).length
  );

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto w-full max-w-[800px] px-4 pb-10 pt-6">
        <div className="mb-6">
          <h1 className="text-[28px] font-bold leading-[36px] text-gray-900">
            Reviews for {tutorName}
          </h1>
          <p className="mt-2 text-[16px] leading-[24px] text-muted">
            Student feedback and ratings
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-border bg-surface-2 p-4 text-[14px] leading-[22px] text-danger">
            {error}
          </div>
        )}

        {/* Rating Summary */}
        {reviews.length > 0 && (
          <div className="mb-6 rounded-2xl border border-border bg-surface-2 p-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="text-center">
                <div className="text-4xl font-bold text-gray-900">{averageRating.toFixed(1)}</div>
                <div className="mt-1 flex justify-center">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <span key={star} className="text-2xl">
                      {star <= Math.round(averageRating) ? "⭐" : "☆"}
                    </span>
                  ))}
                </div>
                <div className="mt-2 text-[14px] text-muted">
                  Based on {reviews.length} review{reviews.length !== 1 ? "s" : ""}
                </div>
              </div>

              <div className="space-y-2">
                {[5, 4, 3, 2, 1].map((rating) => (
                  <div key={rating} className="flex items-center gap-2 text-[14px]">
                    <span className="w-3">{rating}</span>
                    <span className="text-yellow-400">⭐</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-yellow-400 h-2 rounded-full" 
                        style={{ width: `${reviews.length > 0 ? (ratingDistribution[rating - 1] / reviews.length) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="w-8 text-right">{ratingDistribution[rating - 1]}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Reviews List */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8">
              <div className="text-[16px] leading-[24px] text-muted">Loading reviews...</div>
            </div>
          ) : reviews.length === 0 ? (
            <div className="rounded-2xl border border-border bg-surface-2 p-8 text-center">
              <div className="text-[18px] font-semibold leading-[26px] text-gray-900">No reviews yet</div>
              <div className="mt-2 text-[14px] leading-[22px] text-muted">
                Be the first to leave a review for this tutor.
              </div>
            </div>
          ) : (
            reviews.map((review) => (
              <div key={review.id} className="rounded-2xl border border-border bg-surface-2 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="text-[16px] font-semibold text-gray-900">{review.studentName}</div>
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <span key={star} className="text-lg">
                            {star <= review.rating ? "⭐" : "☆"}
                          </span>
                        ))}
                      </div>
                    </div>
                    {review.comment && (
                      <p className="text-[14px] leading-[22px] text-gray-700">{review.comment}</p>
                    )}
                  </div>
                  <div className="text-[12px] text-muted shrink-0">
                    {new Date(review.createdAt).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
