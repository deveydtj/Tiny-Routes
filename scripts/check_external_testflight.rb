#!/usr/bin/env ruby
# Offline check: no Apple login, builds, uploads, or notifications.
require "tmpdir"
$LOADED_FEATURES << "spaceship.rb"

module UI
  def self.user_error!(message) = raise(message)
  def self.message(*) = nil
  def self.success(*) = nil
end

module Spaceship
  module ConnectAPI
    def self.login(*) = nil
    class App
      class << self
        attr_accessor :groups
        def find(*) = new
      end
      def get_beta_groups = self.class.groups
      def bundle_id = "com.tinyroutes.app"
      def id = "6829948652"
    end
  end
end

module FastlaneCore
  class IpaFileAnalyser
    def self.fetch_app_version(*) = "1.0"
    def self.fetch_app_build(*) = "42"
  end
  class BuildWatcher
    class << self
      attr_accessor :arguments
      def wait_for_build_processing_to_be_complete(**args) = self.arguments = args
    end
  end
end

def desc(*) = nil
def lane(_name, &block) = @external = block
def upload_to_testflight(**args) = @upload = args
def assert(condition, message)
  raise message unless condition
end
def expect_error(text, &block)
  block.call
rescue RuntimeError => error
  raise unless error.message.include?(text)
else
  raise "Expected failure containing #{text}"
end

eval(File.read(File.expand_path("../fastlane/Fastfile", __dir__)), binding,
     File.expand_path("../fastlane/Fastfile", __dir__))
ENV.delete("APP_STORE_CONNECT_API_KEY_PATH")
ENV.delete("FASTLANE_USER")
expect_error("Set FASTLANE_USER") { @external.call({}) }
ENV["FASTLANE_USER"] = "offline@example.invalid"
group = Struct.new(:id, :name, :is_internal_group)
Spaceship::ConnectAPI::App.groups = [group.new("internal", "Family and friends", true)]
expect_error("found 0") { @external.call({}) }
assert(@upload.nil?, "An internal group must never trigger an upload")
external = group.new("external-id", "Family and friends", false)
Spaceship::ConnectAPI::App.groups = [external, external]
expect_error("found 2") { @external.call({}) }
Spaceship::ConnectAPI::App.groups = [external]
Dir.mktmpdir do |dir|
  ipa = File.join(dir, "TinyRoutes.ipa")
  File.write(ipa, "offline IPA stand-in")
  @external.call(ipa: ipa)
  assert(@upload[:distribute_only], "Retry must not upload the IPA again")
  assert(@upload.values_at(:app_version, :build_number) == ["1.0", "42"], "Retry must pin the IPA's exact build")
  assert(@upload[:groups] == ["external-id"], "Distribution must target only the verified group")
  assert(@upload[:distribute_external] && @upload[:submit_beta_review] && @upload[:notify_external_testers], "External review and notifications must be enabled")
  assert(FastlaneCore::BuildWatcher.arguments[:build_version] == "42", "Retry must wait for its exact build to process")
end
puts "External TestFlight checks passed"
