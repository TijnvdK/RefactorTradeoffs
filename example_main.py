from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.llm_interaction.handlers.vllm_handler import VLLMHandler
from src.energy_measurement.nvidia_gpu.nvidia_smi_wrapper import GPUEnergyMeter

CODE_SNIPPET_TO_BE_REFACTORED = """
<?php

function getUserData($userId) {
    $users = array();
    for ($i = 0; $i < 1000; $i++) {
        $users[$i] = array(
            'id' => $i,
            'name' => 'User ' . $i,
            'email' => 'user' . $i . '@example.com'
        );
    }

    foreach ($users as $user) {
        if ($user['id'] == $userId) {
            return $user;
        }
    }
    return null;
}

function calculateStats($numbers) {
    $sum = 0;
    for ($i = 0; $i < count($numbers); $i++) {
        $sum += $numbers[$i];
    }

    $avg = $sum / count($numbers);

    $variance = 0;
    for ($i = 0; $i < count($numbers); $i++) {
        $variance += pow($numbers[$i] - $avg, 2);
    }

    return array(
        'sum' => $sum,
        'average' => $avg,
        'variance' => $variance / count($numbers)
    );
}

$data = calculateStats(range(1, 100));
$user = getUserData(42);
echo json_encode($data);
?>
"""

MODELS = ['Qwen/Qwen2.5-Coder-1.5B', 'Qwen/Qwen2.5-Coder-3B']

SYSTEM_PROMPT = 'You are a green software expert. You will receive PHP code snippets and you need to refactor the code snippet to be more efficient and green, with equivalent functionality. You should only return the refactored code, without any explanations or comments.'


def main():
    gpu_energy_meter = GPUEnergyMeter()

    llm_handler = VLLMHandler(
        gpu_memory_utilization=0.8,
        max_model_len=8192,
        max_tokens=8291,
        system_prompt=SYSTEM_PROMPT,
    )

    for model in MODELS:
        llm_handler.change_model(model)

        gpu_energy_meter.start()

        refactored_code = ''
        try:
            refactored_code = llm_handler.send_message(
                f'```{CODE_SNIPPET_TO_BE_REFACTORED}```'
            )
        except LMCallFailed as e:
            print(
                f'Error occurred while sending message for model {model}: {e}'
            )

        print(f'Refactored code for model {model}:\n{refactored_code}\n')

        total_energy_J = gpu_energy_meter.stop()
        print(
            f'Total energy consumed for model {model}: {total_energy_J:.2f} J'
        )

        llm_handler.destroy()


if __name__ == '__main__':
    main()
