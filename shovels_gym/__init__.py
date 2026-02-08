from gymnasium.envs.registration import register

register(
    id="Shovels-v0",
    entry_point="shovels_gym.envs.shovels_env:ShovelsEnv",
)
