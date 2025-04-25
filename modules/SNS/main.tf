resource "aws_sns_topic" "unauthorized_access_topic" {
  name = var.sns_topic_name
}

resource "aws_sns_topic_policy" "accesspolicyforsns" {
  arn = aws_sns_topic.unauthorized_access_topic.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

data "aws_iam_policy_document" "sns_topic_policy" {
  policy_id = "__default_policy_ID"

  statement {
    actions = [
      "SNS:Subscribe",
      "SNS:SetTopicAttributes",
      "SNS:RemovePermission",
      "SNS:Receive",
      "SNS:Publish",
      "SNS:ListSubscriptionsByTopic",
      "SNS:GetTopicAttributes",
      "SNS:DeleteTopic",
      "SNS:AddPermission",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"

      values = [
        var.account-id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = [
        aws_sns_topic.unauthorized_access_topic.arn,
    ]

    sid = "__default_statement_ID"
  }
}

resource "aws_sns_topic_subscription" "name" {
  topic_arn = aws_sns_topic.unauthorized_access_topic.arn
  protocol = "email"
  endpoint = "sujaldyavanapelli80@gmail.com"
  
}