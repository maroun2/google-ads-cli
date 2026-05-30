{
  description = "google-ads-cli — command-line interface for the Google Ads API";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;

        # google-ads is not yet in nixpkgs — build from PyPI sdist
        google-ads = python.pkgs.buildPythonPackage rec {
          pname = "google-ads";
          version = "31.0.0";
          format = "pyproject";

          src = pkgs.fetchPypi {
            pname = "google_ads";
            inherit version;
            hash = "sha256-ZlTgHoubCqKMvkyuHBhqjF4QVQAht2awswfRBtdY8jY=";
          };

          nativeBuildInputs = with python.pkgs; [ setuptools ];

          propagatedBuildInputs = with python.pkgs; [
            google-auth-oauthlib
            google-api-core
            googleapis-common-protos
            grpcio
            grpcio-status
            proto-plus
            pyyaml
            protobuf
          ];

          # Tests require live API credentials
          doCheck = false;
        };

        google-ads-cli = python.pkgs.buildPythonApplication {
          pname = "google-ads-cli";
          version = "1.0.0";
          format = "setuptools";

          src = "${self}/agent-harness";

          propagatedBuildInputs = [
            google-ads
            python.pkgs.click
            python.pkgs.pyyaml
            python.pkgs.google-auth-oauthlib
            python.pkgs.prompt-toolkit
          ];

          # Tests require live API credentials
          doCheck = false;
        };

      in
      {
        packages.default = google-ads-cli;
        packages.google-ads-cli = google-ads-cli;

        apps.default = {
          type = "app";
          program = "${google-ads-cli}/bin/google-ads-cli";
        };
        apps.google-ads-cli = {
          type = "app";
          program = "${google-ads-cli}/bin/google-ads-cli";
        };
      }
    );
}
