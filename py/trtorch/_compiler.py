from typing import List, Dict, Any
import torch
from torch import nn

import trtorch._C
from trtorch._compile_spec import _parse_compile_spec
from trtorch._version import __version__
from trtorch.Device import Device
from types import FunctionType


def compile(module: torch.jit.ScriptModule, compile_spec: Any) -> torch.jit.ScriptModule:
    """Compile a TorchScript module for NVIDIA GPUs using TensorRT

    Takes a existing TorchScript module and a set of settings to configure the compiler
    and will convert methods to JIT Graphs which call equivalent TensorRT engines

    Converts specifically the forward method of a TorchScript Module

    Args:
        module (torch.jit.ScriptModule): Source module, a result of tracing or scripting a PyTorch
            ``torch.nn.Module``
        compile_spec (dict): Compilation settings including operating precision, target device, etc.
            One key is required which is ``inputs``, describing the input sizes or ranges for inputs
            to the graph as well as expect types and formats for those inputs. All other keys are optional

            .. code-block:: py

                compile_spec = {
                    "inputs": [
                        trtorch.Input((1, 3, 224, 224)), # Static NCHW input shape for input #1
                        trtorch.Input(
                            min_shape=(1, 224, 224, 3),
                            opt_shape=(1, 512, 512, 3),
                            max_shape=(1, 1024, 1024, 3),
                            dtype=torch.int32
                            format=torch.channel_last
                        ) # Dynamic input shape for input #2
                    ],
                    "device": {
                        "device_type": torch.device("cuda"), # Type of device to run engine on (for DLA use trtorch.DeviceType.DLA)
                        "gpu_id": 0, # Target gpu id to run engine (Use Xavier as gpu id for DLA)
                        "dla_core": 0, # (DLA only) Target dla core id to run engine
                        "allow_gpu_fallback": false, # (DLA only) Allow layers unsupported on DLA to run on GPU
                    },
                    "disable_tf32": False, # Force FP32 layers to use traditional as FP32 format vs the default behavior of rounding the inputs to 10-bit mantissas before multiplying, but accumulates the sum using 23-bit mantissas
                    "sparse_weights": Enable sparsity for convolution and fully connected layers.
                    "enabled_precisions": {torch.float, torch.half}, # Enabling FP16 kernels
                    "refit": false, # enable refit
                    "debug": false, # enable debuggable engine
                    "strict_types": false, # kernels should strictly run in operating precision
                    "capability": trtorch.EngineCapability.DEFAULT, # Restrict kernel selection to safe gpu kernels or safe dla kernels
                    "num_min_timing_iters": 2, # Number of minimization timing iterations used to select kernels
                    "num_avg_timing_iters": 1, # Number of averaging timing iterations used to select kernels
                    "workspace_size": 0, # Maximum size of workspace given to TensorRT
                    "max_batch_size": 0, # Maximum batch size (must be >= 1 to be set, 0 means not set)
                    "torch_fallback": {
                        "enabled": True, # Turn on or turn off falling back to PyTorch if operations are not supported in TensorRT
                        "force_fallback_ops": [
                            "aten::max_pool2d" # List of specific ops to require running in PyTorch
                        ],
                        "force_fallback_modules": [
                            "mypymod.mytorchmod" # List of specific torch modules to require running in PyTorch
                        ],
                        "min_block_size": 3 # Minimum number of ops an engine must incapsulate to be run in TensorRT
                    }
                }

            Input Sizes can be specified as torch sizes, tuples or lists. dtypes can be specified using
            torch datatypes or trtorch datatypes and you can use either torch devices or the trtorch device type enum
            to select device type.

    Returns:
        torch.jit.ScriptModule: Compiled TorchScript Module, when run it will execute via TensorRT
    """

    if isinstance(module, torch.jit.ScriptFunction):
        raise TypeError(
            "torch.jit.ScriptFunction currently is not directly supported, wrap the function in a module to compile")

    parsed_spec = _parse_compile_spec(compile_spec)
    compiled_cpp_mod = trtorch._C.compile_graph(module._c, _parse_compile_spec(compile_spec))
    compiled_module = torch.jit._recursive.wrap_cpp_module(compiled_cpp_mod)
    return compiled_module


def convert_method_to_trt_engine(module: torch.jit.ScriptModule, method_name: str, compile_spec: Any) -> str:
    """Convert a TorchScript module method to a serialized TensorRT engine

    Converts a specified method of a module to a serialized TensorRT engine given a dictionary of conversion settings

    Args:
        module (torch.jit.ScriptModule): Source module, a result of tracing or scripting a PyTorch
            ``torch.nn.Module``
        method_name (str): Name of method to convert
        compile_spec (dict): Compilation settings including operating precision, target device, etc.
            One key is required which is ``inputs``, describing the input sizes or ranges for inputs
            to the graph as well as expect types and formats for those inputs. All other keys are optional

            .. code-block:: py

                CompileSpec = {
                    "inputs": [
                        trtorch.Input((1, 3, 224, 224)), # Static NCHW input shape for input #1
                        trtorch.Input(
                            min_shape=(1, 224, 224, 3),
                            opt_shape=(1, 512, 512, 3),
                            max_shape=(1, 1024, 1024, 3),
                            dtype=torch.int32
                            format=torch.channel_last
                        ) # Dynamic input shape for input #2
                    ],
                    "device": {
                        "device_type": torch.device("cuda"), # Type of device to run engine on (for DLA use trtorch.DeviceType.DLA)
                        "gpu_id": 0, # Target gpu id to run engine (Use Xavier as gpu id for DLA)
                        "dla_core": 0, # (DLA only) Target dla core id to run engine
                        "allow_gpu_fallback": false, # (DLA only) Allow layers unsupported on DLA to run on GPU
                    },
                    "enabled_precisions": {torch.float, torch.half}, # Enabling FP16 kernels
                    # List of datatypes that should be configured for each input. Supported options torch.{float|half|int8|int32|bool}.
                    "disable_tf32": False, # Force FP32 layers to use traditional as FP32 format vs the default behavior of rounding the inputs to 10-bit mantissas before multiplying, but accumulates the sum using 23-bit mantissas
                    "sparse_weights": Enable sparsity for convolution and fully connected layers.
                    "refit": false, # enable refit
                    "debug": false, # enable debuggable engine
                    "strict_types": false, # kernels should strictly run in operating precision
                    "capability": trtorch.EngineCapability.DEFAULT, # Restrict kernel selection to safe gpu kernels or safe dla kernels
                    "num_min_timing_iters": 2, # Number of minimization timing iterations used to select kernels
                    "num_avg_timing_iters": 1, # Number of averaging timing iterations used to select kernels
                    "workspace_size": 0, # Maximum size of workspace given to TensorRT
                    "max_batch_size": 0, # Maximum batch size (must be >= 1 to be set, 0 means not set)
                }

            Input Sizes can be specified as torch sizes, tuples or lists. dtypes can be specified using
            torch datatypes or trtorch datatypes and you can use either torch devices or the trtorch device type enum
            to select device type.

    Returns:
        bytes: Serialized TensorRT engine, can either be saved to a file or deserialized via TensorRT APIs
    """
    if isinstance(module, torch.jit.ScriptFunction):
        raise TypeError(
            "torch.jit.ScriptFunctions currently are not directly supported, wrap the function in a module to compile")

    return trtorch._C.convert_graph_to_trt_engine(module._c, method_name, _parse_compile_spec(compile_spec))


def embed_engine_in_new_module(serialized_engine: bytes, device: Device) -> torch.jit.ScriptModule:
    """Takes a pre-built serialized TensorRT engine and embeds it within a TorchScript module

    Takes a pre-built serialied TensorRT engine (as bytes) and embeds it within a TorchScript module.
    Registers the forward method to execute the TensorRT engine with the function signature:

        forward(Tensor[]) -> Tensor[]

    Module can be save with engine embedded with torch.jit.save and moved / loaded according to TRTorch portability rules

    Args:
        serialized_engine (bytes): Serialized TensorRT engine from either TRTorch or TensorRT APIs

    Returns:
        torch.jit.ScriptModule: New TorchScript module with engine embedded
    """
    cpp_mod = trtorch._C.embed_engine_in_new_module(serialized_engine, device._to_internal())
    return torch.jit._recursive.wrap_cpp_module(cpp_mod)


def check_method_op_support(module: torch.jit.ScriptModule, method_name: str) -> bool:
    """Checks to see if a method is fully supported by TRTorch

    Checks if a method of a TorchScript module can be compiled by TRTorch, if not, a list of operators
    that are not supported are printed out and the function returns false, else true.

    Args:
        module (torch.jit.ScriptModule): Source module, a result of tracing or scripting a PyTorch
            ``torch.nn.Module``
        method_name (str): Name of method to check

    Returns:
        bool: True if supported Method
    """
    return trtorch._C.check_method_op_support(module._c, method_name)


def dump_build_info():
    """Prints build information about the TRTorch distribution to stdout
    """
    print(get_build_info())


def get_build_info() -> str:
    """Returns a string containing the build information of TRTorch distribution

    Returns:
        str: String containing the build information for TRTorch distribution
    """
    build_info = trtorch._C.get_build_info()
    build_info = "TRTorch Version: " + str(__version__) + '\n' + build_info
    return build_info


def set_device(gpu_id):
    trtorch._C.set_device(gpu_id)
