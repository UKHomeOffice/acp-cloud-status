terraform {
  backend "s3" {
    bucket         = "tfstate-acp-test-58bb4bb962af"
    region         = "eu-west-2"
    key            = "sre.tfstate"
    encrypt        = "true"
    dynamodb_table = "tfstate-acp-test-58bb4bb962af"
  }
}

provider "aws" {
  region  = "eu-west-2"
  version = "~> 3.0"
  profile = "appvia"
}
