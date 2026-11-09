<?php

namespace App\Http\Requests;

use App\Enums\AnalysisMode;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules\File;

class StoreAnalysisRequest extends FormRequest
{
    public function rules(): array
    {
        $upload = config('figurepose.upload');

        return [
            // IMG-05 / IMG-06: format, size and dimensions.
            'image' => [
                'required',
                File::types($upload['mimes'])->max($upload['max_kb']),
                Rule::dimensions()
                    ->minWidth($upload['min_dimension'])->minHeight($upload['min_dimension'])
                    ->maxWidth($upload['max_dimension'])->maxHeight($upload['max_dimension']),
            ],
            'analysis_mode' => ['required', Rule::enum(AnalysisMode::class)],
            // Manual mode means the user picked the profile (FIG-03).
            'figure_profile_id' => [
                Rule::requiredIf(fn () => $this->input('analysis_mode') === AnalysisMode::Manual->value),
                'nullable', 'integer', Rule::exists('figure_profiles', 'id')->where('is_active', true),
            ],
            'figure_id' => ['nullable', 'integer', Rule::exists('figures', 'id')->where('user_id', $this->user('sanctum')?->id ?? 0)],
        ];
    }

    public function messages(): array
    {
        $upload = config('figurepose.upload');

        return [
            'image.dimensions' => "The photo must be between {$upload['min_dimension']} and {$upload['max_dimension']} pixels on each side.",
            'image.mimes' => 'Use a JPEG, PNG or WebP photo.',
            'image.max' => 'The photo must be '.intdiv($upload['max_kb'], 1024).' MB or smaller.',
            'figure_profile_id.required' => 'Pick a figure type, or switch to automatic mode.',
            'figure_id.exists' => 'That figure is not in your collection.',
        ];
    }
}
