<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreFigureRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:120'],
            'brand' => ['nullable', 'string', 'max:80'],
            'figure_profile_id' => ['required', 'integer', Rule::exists('figure_profiles', 'id')->where('is_active', true)],
            // Known joint limits for this exact figure, keyed by joint name (PRD 8.5).
            'articulation_config' => ['nullable', 'array'],
            'articulation_config.*.min' => ['required_with:articulation_config', 'numeric', 'between:0,360'],
            'articulation_config.*.max' => ['required_with:articulation_config', 'numeric', 'between:0,360'],
        ];
    }

    public function messages(): array
    {
        return [
            'figure_profile_id.exists' => 'Pick one of the supported figure types.',
        ];
    }
}
