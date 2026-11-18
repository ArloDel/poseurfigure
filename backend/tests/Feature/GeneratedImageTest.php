<?php

namespace Tests\Feature;

use App\Enums\AnalysisMode;
use App\Enums\AnalysisStatus;
use App\Enums\GenerationStatus;
use App\Enums\ValidationStatus;
use App\Jobs\GeneratePoseImage;
use App\Models\Analysis;
use App\Models\FigureProfile;
use App\Models\GeneratedImage;
use App\Models\PoseCatalog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class GeneratedImageTest extends TestCase
{
    use RefreshDatabase;

    private string $guestKey;

    private Analysis $analysis;

    private PoseCatalog $pose;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        config(['figurepose.generation.enabled' => true]);
        Storage::fake('s3');
        Storage::disk('s3')->put('analyses/x/photo.jpg', 'photo-bytes');
        $this->guestKey = (string) Str::uuid();
        $this->pose = PoseCatalog::where('slug', 'rider-ready-stance')->firstOrFail();
        $this->analysis = $this->analysis($this->guestKey);
    }

    private function analysis(string $guestKey, array $attrs = []): Analysis
    {
        return Analysis::create($attrs + [
            'guest_key_hash' => Analysis::hashGuestKey($guestKey),
            'figure_profile_id' => FigureProfile::where('slug', 'humanoid_v1')->value('id'),
            'analysis_mode' => AnalysisMode::Automatic,
            'status' => AnalysisStatus::Completed,
            'pose_data' => ['pose' => ['keypoints' => ['neck' => ['x' => 0.5, 'y' => 0.2, 'visibility' => 'visible']]]],
            'image_disk' => 's3', 'image_path' => 'analyses/x/photo.jpg', 'image_mime' => 'image/jpeg',
            'image_size' => 5, 'image_width' => 900, 'image_height' => 1200,
        ]);
    }

    private function generate(array $body = [], ?string $guestKey = null, ?PoseCatalog $pose = null)
    {
        return $this->withHeader('X-Guest-Key', $guestKey ?? $this->guestKey)->postJson(
            '/api/v1/poses/'.($pose ?? $this->pose)->id.'/generate',
            $body + ['analysis_id' => $this->analysis->public_id, 'consent' => true],
        );
    }

    private function fakeAi(string $validation = 'validated'): void
    {
        Http::fake(['*/v1/generate' => Http::response([
            'provider' => 'stub', 'prompt' => 'Redraw...', 'image_base64' => base64_encode('jpeg-bytes'), 'mime' => 'image/jpeg',
            'width' => 768, 'height' => 800,
            'validation' => ['status' => $validation, 'similarity' => 0.93, 'reason' => $validation === 'rejected' ? 'pose_mismatch' : null],
        ])]);
    }

    private function runJob(GeneratedImage $image): GeneratedImage
    {
        app()->call([new GeneratePoseImage($image->id), 'handle']);

        return $image->fresh();
    }

    public function test_generation_needs_explicit_consent(): void
    {
        Queue::fake();

        $this->generate(['consent' => false])->assertStatus(422)->assertJsonValidationErrors('consent');
        $this->withHeader('X-Guest-Key', $this->guestKey)
            ->postJson("/api/v1/poses/{$this->pose->id}/generate", ['analysis_id' => $this->analysis->public_id])
            ->assertStatus(422)->assertJsonValidationErrors('consent');

        $this->assertSame(0, GeneratedImage::count());
        Queue::assertNothingPushed();
    }

    public function test_request_is_queued_and_labelled_ai_generated(): void
    {
        Queue::fake();

        $this->generate(['mirrored' => true])
            ->assertStatus(202)
            ->assertJsonPath('data.status', 'pending')
            ->assertJsonPath('data.validation_status', 'unvalidated')
            ->assertJsonPath('data.ai_generated', true)
            ->assertJsonPath('data.source', 'ai_generated')
            ->assertJsonPath('data.mirrored', true)
            ->assertJsonPath('data.image_url', null);

        $image = GeneratedImage::firstOrFail();
        $this->assertNotNull($image->consented_at);
        Queue::assertPushed(GeneratePoseImage::class, fn ($job) => $job->generatedImageId === $image->id);
    }

    public function test_repeating_the_request_does_not_generate_twice(): void
    {
        Queue::fake();

        $first = $this->generate()->json('data.id');
        $second = $this->generate()->assertStatus(202)->json('data.id'); // still pending, same visual

        $this->assertSame($first, $second);
        $this->assertSame(1, GeneratedImage::count());
        Queue::assertPushed(GeneratePoseImage::class, 1);

        // Mirrored is a different image.
        $this->generate(['mirrored' => true])->assertStatus(202);
        $this->assertSame(2, GeneratedImage::count());
    }

    public function test_job_sends_photo_and_target_then_stores_a_validated_image_privately(): void
    {
        Queue::fake();
        $this->fakeAi('validated');
        $id = $this->generate()->json('data.id');

        $image = $this->runJob(GeneratedImage::findOrFail($id));

        Http::assertSent(function ($request) {
            $body = $request->body();

            return str_contains($body, 'photo-bytes') && str_contains($body, 'humanoid_v1') && str_contains($body, 'left_elbow');
        });
        $this->assertSame(GenerationStatus::Generated, $image->generation_status);
        $this->assertSame(ValidationStatus::Validated, $image->validation_status);
        $this->assertSame('stub', $image->provider);
        $this->assertStringStartsWith('generated/', $image->image_path);
        Storage::disk('s3')->assertExists($image->image_path);
        $this->assertSame(0.93, $image->details['validation']['similarity']);
    }

    public function test_rejected_image_is_marked_and_explained(): void
    {
        Queue::fake();
        $this->fakeAi('rejected');
        $image = $this->runJob(GeneratedImage::findOrFail($this->generate()->json('data.id')));

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/generated-images/{$image->id}")
            ->assertOk()
            ->assertJsonPath('data.status', 'generated')
            ->assertJsonPath('data.validation_status', 'rejected')
            ->assertJsonPath('data.validation_note', "This image doesn't show the target pose reliably. Follow the catalog steps instead.");
    }

    public function test_image_is_served_only_through_a_signed_expiring_link(): void
    {
        Queue::fake();
        $this->fakeAi();
        $image = $this->runJob(GeneratedImage::findOrFail($this->generate()->json('data.id')));

        $url = $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/generated-images/{$image->id}")->json('data.image_url');
        $this->flushHeaders();

        $this->get($url)->assertOk()->assertHeader('Content-Type', 'image/jpeg');
        $this->assertSame('jpeg-bytes', $this->get($url)->getContent());
        $this->getJson("/api/v1/generated-images/{$image->id}/file")->assertForbidden();
        $this->getJson($url.'x')->assertForbidden();

        $this->travel(16)->minutes();
        $this->getJson($url)->assertForbidden();
    }

    public function test_only_the_owner_can_request_or_see_a_visual(): void
    {
        Queue::fake();
        $image = GeneratedImage::findOrFail($this->generate()->json('data.id'));
        $stranger = (string) Str::uuid();

        $this->generate([], $stranger)->assertNotFound();
        $this->withHeader('X-Guest-Key', $stranger)->getJson("/api/v1/generated-images/{$image->id}")->assertNotFound();
    }

    public function test_pose_must_fit_the_figure_type_and_the_analysis_must_be_finished(): void
    {
        Queue::fake();
        $mecha = PoseCatalog::where('slug', 'rifle-aim')->firstOrFail();
        $this->generate([], null, $mecha)->assertStatus(422);

        $this->analysis->update(['status' => AnalysisStatus::Processing]);
        $this->generate()->assertStatus(409);
    }

    public function test_daily_limit_and_feature_switch(): void
    {
        Queue::fake();
        config(['figurepose.generation.daily_limit' => 1]);
        $this->generate()->assertStatus(202);
        $other = PoseCatalog::where('slug', 'fencing-lunge')->firstOrFail();
        $this->generate([], null, $other)->assertStatus(429);

        // The same visual again is still returned (202: still pending): it costs nothing.
        $this->generate()->assertStatus(202);

        config(['figurepose.generation.enabled' => false]);
        $this->generate([], null, $other)->assertStatus(503);
        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$this->analysis->public_id}")
            ->assertJsonPath('data.ai_visuals_available', false);
    }

    public function test_failed_generation_can_be_requested_again(): void
    {
        Queue::fake();
        $image = GeneratedImage::findOrFail($this->generate()->json('data.id'));
        (new GeneratePoseImage($image->id))->failed(new \RuntimeException('provider down'));

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/generated-images/{$image->id}")
            ->assertJsonPath('data.status', 'failed')
            ->assertJsonPath('data.error.message', "We couldn't make this visual. Try again in a few minutes.");

        $this->generate()->assertStatus(202)->assertJsonPath('data.id', $image->id)->assertJsonPath('data.status', 'pending');
        Queue::assertPushed(GeneratePoseImage::class, 2);
    }

    public function test_deleting_the_analysis_deletes_its_visuals(): void
    {
        Queue::fake();
        $this->fakeAi();
        $image = $this->runJob(GeneratedImage::findOrFail($this->generate()->json('data.id')));

        $this->withHeader('X-Guest-Key', $this->guestKey)->deleteJson("/api/v1/analyses/{$this->analysis->public_id}")->assertOk();

        Storage::disk('s3')->assertMissing($image->image_path);
        $this->assertSame(0, GeneratedImage::count());
    }

    public function test_the_catalog_photo_of_the_target_pose_is_sent_as_a_reference(): void
    {
        Queue::fake();
        $this->fakeAi();
        $this->runJob(GeneratedImage::findOrFail($this->generate()->json('data.id')));

        $catalogPhoto = file_get_contents(public_path($this->pose->reference_image));
        Http::assertSent(fn ($request) => str_contains($request->body(), 'name="reference"')
            && str_contains($request->body(), substr($catalogPhoto, 0, 200)));
    }

    public function test_a_result_that_matches_mirrored_says_so(): void
    {
        Queue::fake();
        Http::fake(['*/v1/generate' => Http::response([
            'provider' => 'openai', 'prompt' => 'p', 'image_base64' => base64_encode('jpeg-bytes'), 'mime' => 'image/jpeg',
            'width' => 1024, 'height' => 1536,
            'validation' => ['status' => 'validated', 'similarity' => 0.87, 'mirrored' => true],
        ])]);
        $image = $this->runJob(GeneratedImage::findOrFail($this->generate()->json('data.id')));

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/generated-images/{$image->id}")
            ->assertJsonPath('data.provider', 'openai')
            ->assertJsonPath('data.shown_mirrored', true)
            ->assertJsonPath('data.validation_note', 'The pose in this image matches the target pose, mirrored left to right. It is not proof your figure can hold it.');
    }

    public function test_a_refused_request_fails_at_once_instead_of_paying_for_a_retry(): void
    {
        Queue::fake();
        Http::fake(['*/v1/generate' => Http::response(['detail' => 'OpenAI returned 400: moderation_blocked'], 422)]);
        $image = GeneratedImage::findOrFail($this->generate()->json('data.id'));

        $job = (new GeneratePoseImage($image->id))->withFakeQueueInteractions();
        app()->call([$job, 'handle']);

        $job->assertFailed();
    }

    public function test_the_analysis_names_the_image_service_for_the_consent_sheet(): void
    {
        config(['figurepose.generation.provider_name' => 'OpenAI']);
        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/analyses/{$this->analysis->public_id}")
            ->assertJsonPath('data.ai_visuals_provider', 'OpenAI');
    }

    public function test_a_declined_photo_is_explained_instead_of_suggesting_a_retry(): void
    {
        Queue::fake();
        $image = GeneratedImage::findOrFail($this->generate()->json('data.id'));
        $declined = new \Illuminate\Http\Client\RequestException(
            new \Illuminate\Http\Client\Response(new \GuzzleHttp\Psr7\Response(422, [], '{"detail":"OpenAI returned 400: moderation_blocked"}')));

        (new GeneratePoseImage($image->id))->failed($declined);

        $this->withHeader('X-Guest-Key', $this->guestKey)->getJson("/api/v1/generated-images/{$image->id}")
            ->assertJsonPath('data.status', 'failed')
            ->assertJsonPath('data.error.message', "The image service declined this photo, so there's no AI visual for it. The steps above still work.");
    }
}
