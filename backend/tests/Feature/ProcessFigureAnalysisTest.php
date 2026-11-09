<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Jobs\ProcessFigureAnalysis;
use App\Models\Analysis;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class ProcessFigureAnalysisTest extends TestCase
{
    use RefreshDatabase;

    private Analysis $analysis;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
        Storage::disk('s3')->put('analyses/2026/11/photo.jpg', 'fake-bytes');

        $this->analysis = Analysis::create([
            'guest_key_hash' => Analysis::hashGuestKey('00000000-0000-4000-8000-000000000000'),
            'analysis_mode' => AnalysisMode::Automatic,
            'status' => AnalysisStatus::Pending,
            'image_disk' => 's3',
            'image_path' => 'analyses/2026/11/photo.jpg',
            'image_mime' => 'image/jpeg',
            'image_size' => 10,
            'image_width' => 900,
            'image_height' => 1200,
        ]);
    }

    private function run_job(): void
    {
        app()->call([new ProcessFigureAnalysis($this->analysis->id), 'handle']);
        $this->analysis->refresh();
    }

    public function test_good_photo_completes(): void
    {
        Http::fake(['*/v1/analyze' => Http::response([
            'model_version' => 'quality-0.1', 'stage' => 'quality_only',
            'quality' => ['ok' => true, 'issues' => [], 'sharpness' => 210.5], 'pose' => null,
        ])]);

        $this->run_job();

        $this->assertSame(AnalysisStatus::Completed, $this->analysis->status);
        $this->assertSame('quality-0.1', $this->analysis->ai_model_version);
        $this->assertSame(1, $this->analysis->attempts);
        Http::assertSent(fn ($req) => $req->hasHeader('X-Request-Id', $this->analysis->public_id));
    }

    public function test_unsuitable_photo_fails_with_a_clear_reason(): void
    {
        Http::fake(['*/v1/analyze' => Http::response([
            'model_version' => 'quality-0.1', 'stage' => 'quality_only', 'pose' => null,
            'quality' => ['ok' => false, 'issues' => [['code' => 'blurry', 'message' => 'This photo is too blurry to read the joints.']]],
        ])]);

        $this->run_job();

        $this->assertSame(AnalysisStatus::Failed, $this->analysis->status);
        $this->assertSame('blurry', $this->analysis->failure_code);
    }

    public function test_ai_outage_throws_so_the_queue_retries_then_marks_failed(): void
    {
        Http::fake(['*/v1/analyze' => Http::response('boom', 500)]);

        try {
            $this->run_job();
            $this->fail('Expected the job to throw so the queue retries it.');
        } catch (RequestException) {
            // expected
        }
        $this->assertSame(AnalysisStatus::Processing, $this->analysis->fresh()->status);

        (new ProcessFigureAnalysis($this->analysis->id))->failed(new \RuntimeException('down'));

        $fresh = $this->analysis->fresh();
        $this->assertSame(AnalysisStatus::Failed, $fresh->status);
        $this->assertSame('ai_unavailable', $fresh->failure_code);
    }

    public function test_finished_analysis_is_not_processed_again(): void
    {
        Http::fake();
        $this->analysis->update(['status' => AnalysisStatus::Completed]);

        $this->run_job();

        Http::assertNothingSent();
    }
}
