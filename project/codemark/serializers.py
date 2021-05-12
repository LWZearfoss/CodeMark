from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer
from .models import Result, LevelOutput, StepOutput, RunStepOutput, TestStepOutput


class TestStepOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStepOutput
        exclude = ('number',)


class RunStepOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunStepOutput
        exclude = ('number',)


class StepOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepOutput
        exclude = ('number',)


class StepOutputPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        StepOutput: StepOutputSerializer,
        RunStepOutput: RunStepOutputSerializer,
        TestStepOutput: TestStepOutputSerializer
    }


class LevelOutputSerializer(serializers.ModelSerializer):
    step_outputs = StepOutputPolymorphicSerializer(many=True, read_only=True)

    class Meta:
        model = LevelOutput
        fields = '__all__'


class ResultSerializer(serializers.ModelSerializer):
    level_outputs = LevelOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Result
        fields = '__all__'
