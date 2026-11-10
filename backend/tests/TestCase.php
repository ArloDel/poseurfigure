<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use RuntimeException;

abstract class TestCase extends BaseTestCase
{
    /**
     * Runs when the test application boots, before RefreshDatabase touches the database.
     * Container env vars (DB_CONNECTION=pgsql) can override phpunit.xml, and a test run
     * would then empty the development database. Refuse to continue unless the database is in-memory SQLite.
     */
    protected function refreshApplication()
    {
        parent::refreshApplication();

        $connection = config('database.default');
        $database = config("database.connections.{$connection}.database");

        if ($connection !== 'sqlite' || $database !== ':memory:') {
            throw new RuntimeException(
                "Tests must use in-memory SQLite, but the database is [{$connection}: {$database}]. ".
                'Check the <server> and <env> entries in phpunit.xml.'
            );
        }
    }
}
