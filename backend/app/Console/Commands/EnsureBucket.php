<?php

namespace App\Console\Commands;

use Aws\S3\Exception\S3Exception;
use Aws\S3\S3Client;
use Illuminate\Console\Command;

/** Creates the private image bucket on S3/MinIO if it does not exist yet. Safe to run on every start. */
class EnsureBucket extends Command
{
    protected $signature = 'figurepose:ensure-bucket {--disk=s3}';

    protected $description = 'Create the private image bucket if it is missing';

    public function handle(): int
    {
        $config = config('filesystems.disks.'.$this->option('disk'));

        if (($config['driver'] ?? null) !== 's3') {
            $this->info('Disk is not S3, nothing to do.');

            return self::SUCCESS;
        }

        $client = new S3Client([
            'version' => 'latest',
            'region' => $config['region'] ?: 'us-east-1',
            'endpoint' => $config['endpoint'] ?: null,
            'use_path_style_endpoint' => (bool) $config['use_path_style_endpoint'],
            'credentials' => ['key' => $config['key'], 'secret' => $config['secret']],
        ]);

        $bucket = $config['bucket'];

        if ($client->doesBucketExistV2($bucket)) {
            $this->info("Bucket [{$bucket}] exists.");

            return self::SUCCESS;
        }

        try {
            $client->createBucket(['Bucket' => $bucket]);
            $this->info("Bucket [{$bucket}] created (private).");
        } catch (S3Exception $e) {
            $this->error("Could not create bucket [{$bucket}]: {$e->getAwsErrorMessage()}");

            return self::FAILURE;
        }

        return self::SUCCESS;
    }
}
